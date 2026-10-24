"""Train the edge anomaly model: a 1-D convolutional autoencoder over 10-second ECG windows.

Semi-supervised: trained on *healthy* windows only. At inference the reconstruction error
(MSE between the window and its reconstruction) is the anomaly score — windows unlike
anything seen in training reconstruct badly.

Data: synthetic windows from edge/simulator/generator.py (the same generator the live demo
uses). Splits are generated from independent RNG seeds so no window appears in two splits.
MIT-BIH training is the next step; the preprocessing and export path here stays the same.

Outputs (ai-models/models/):
  ecg_autoencoder.onnx      the model, opset 17, input "ecg" float32 [N, 1, 1248]
  ecg_autoencoder.json      preprocessing contract, thresholds, metrics
  training_report.md        human-readable summary

    python ai-models/training/train_autoencoder.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import torch
from torch import nn

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "edge"))
from simulator.generator import generate_window  # noqa: E402

OUT = ROOT / "ai-models" / "models"
WIN = 1248            # 1,250 samples cropped to a multiple of 16 (four stride-2 layers)
SEED = 42

ANOMALY_PROFILES = ("tachycardia", "bradycardia", "arrhythmia", "hypoxia")


def preprocess(ecg: np.ndarray) -> np.ndarray:
    """Per-window z-score + crop. Must match edge/edge_inference/model.py exactly."""
    x = np.asarray(ecg, dtype=np.float32)[:WIN]
    return (x - x.mean()) / (x.std() + 1e-6)


def make_set(profile: str, n: int, seed: int):
    rng = np.random.default_rng(seed)
    xs, acts, aux = [], [], []
    for _ in range(n):
        w = generate_window(profile, rng)
        xs.append(preprocess(w.ecg))
        acts.append(w.activity)
        aux.append((w.hr_stats["mean"], w.spo2))
    return np.stack(xs)[:, None, :], np.array(acts), np.array(aux, dtype=np.float32)


class ConvAutoencoder(nn.Module):
    def __init__(self):
        super().__init__()
        c = [1, 16, 32, 32, 16]
        enc = []
        for a, b in zip(c, c[1:]):
            enc += [nn.Conv1d(a, b, 7, stride=2, padding=3), nn.ReLU()]
        self.encoder = nn.Sequential(*enc)                    # [N,16,78] bottleneck
        dec = []
        r = c[::-1]
        for i, (a, b) in enumerate(zip(r, r[1:])):
            dec.append(nn.ConvTranspose1d(a, b, 8, stride=2, padding=3))
            if i < len(r) - 2:
                dec.append(nn.ReLU())
        self.decoder = nn.Sequential(*dec)

    def forward(self, x):
        return self.decoder(self.encoder(x))


def errors(model, x, bs=256):
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(x), bs):
            xb = torch.from_numpy(x[i:i + bs])
            out.append(((model(xb) - xb) ** 2).mean(dim=(1, 2)).numpy())
    return np.concatenate(out)


def auc(neg, pos):
    """ROC-AUC via the rank-sum formulation (no sklearn dependency)."""
    s = np.concatenate([neg, pos])
    ranks = s.argsort().argsort() + 1
    rp = ranks[len(neg):].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def main():
    torch.manual_seed(SEED)
    t0 = time.time()
    print("generating data …", flush=True)
    xtr, _, _ = make_set("healthy", 4000, seed=1)
    xva, act_va, _ = make_set("healthy", 1000, seed=2)
    test = {"healthy": make_set("healthy", 1000, seed=3)}
    for i, p in enumerate(ANOMALY_PROFILES):
        test[p] = make_set(p, 500, seed=10 + i)

    model = ConvAutoencoder()
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=25)
    xt = torch.from_numpy(xtr)
    history = []
    for epoch in range(25):
        model.train()
        perm = torch.randperm(len(xt))
        tot = 0.0
        for i in range(0, len(xt), 64):
            xb = xt[perm[i:i + 64]]
            loss = ((model(xb) - xb) ** 2).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(xb)
        sched.step()
        val = float(errors(model, xva).mean())
        history.append({"epoch": epoch + 1, "train_mse": tot / len(xt), "val_mse": val})
        print(f"epoch {epoch+1:2d}  train {tot/len(xt):.5f}  val {val:.5f}", flush=True)

    # Thresholds from the healthy *validation* set only, per activity (motion raises error).
    e_va = errors(model, xva)
    thr = {}
    for a in ("rest", "walk", "run"):
        ea = e_va[act_va == a]
        thr[a] = {"tau_low": float(np.quantile(ea, 0.99)), "tau_high": float(np.quantile(ea, 0.999) * 1.5)}

    def flag(e, acts):
        lo = np.array([thr[a]["tau_low"] for a in acts])
        return e >= lo

    metrics = {}
    e_h = errors(model, test["healthy"][0])
    fp = flag(e_h, test["healthy"][1])
    metrics["healthy"] = {"n": len(e_h), "false_positive_rate": float(fp.mean())}
    all_pos_e, all_pos_flag = [], []
    for p in ANOMALY_PROFILES:
        e_p = errors(model, test[p][0])
        fl = flag(e_p, test[p][1])
        all_pos_e.append(e_p)
        all_pos_flag.append(fl)
        metrics[p] = {"n": len(e_p), "recall": float(fl.mean()), "roc_auc": auc(e_h, e_p)}
    pos_flag = np.concatenate(all_pos_flag)
    tp, fn, fpn = pos_flag.sum(), (~pos_flag).sum(), fp.sum()
    precision = tp / max(tp + fpn, 1)
    recall = tp / (tp + fn)
    metrics["overall"] = {
        "precision": float(precision), "recall": float(recall),
        "f1": float(2 * precision * recall / max(precision + recall, 1e-9)),
        "roc_auc": auc(e_h, np.concatenate(all_pos_e)),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    onnx_path = OUT / "ecg_autoencoder.onnx"
    model.eval()
    torch.onnx.export(model, torch.zeros(1, 1, WIN), str(onnx_path), input_names=["ecg"],
                      output_names=["reconstruction"], dynamic_axes={"ecg": {0: "batch"}, "reconstruction": {0: "batch"}},
                      opset_version=17, dynamo=False)

    # Verify the exported file reproduces PyTorch exactly.
    import onnxruntime as ort
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    xs = test["arrhythmia"][0][:8]
    diff = float(np.abs(sess.run(None, {"ecg": xs})[0] - model(torch.from_numpy(xs)).detach().numpy()).max())
    t1 = time.perf_counter()
    for _ in range(200):
        sess.run(None, {"ecg": xs[:1]})
    infer_ms = (time.perf_counter() - t1) / 200 * 1000

    meta = {
        "model": "ecg_autoencoder", "version": "ae-onnx-1.0.0", "architecture": "1-D conv autoencoder, 4+4 layers",
        "parameters": int(n_params), "onnx_bytes": onnx_path.stat().st_size, "opset": 17,
        "input": {"name": "ecg", "shape": [None, 1, WIN], "sample_rate_hz": 125,
                  "preprocessing": "first 1248 samples of a 10 s single-lead window, per-window z-score"},
        "score": "mean squared reconstruction error", "thresholds_by_activity": thr,
        "training_data": "synthetic healthy windows from edge/simulator (4000 train / 1000 val, independent seeds)",
        "metrics_test": metrics, "onnx_vs_pytorch_max_abs_diff": diff, "cpu_inference_ms": infer_ms,
        "history": history, "train_seconds": round(time.time() - t0, 1),
    }
    (OUT / "ecg_autoencoder.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: meta[k] for k in ("parameters", "onnx_bytes", "cpu_inference_ms", "onnx_vs_pytorch_max_abs_diff")}, indent=1))
    print(json.dumps(metrics, indent=1))


if __name__ == "__main__":
    main()
