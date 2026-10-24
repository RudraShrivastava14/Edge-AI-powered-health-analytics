"""Edge model: a deliberately tiny neural network that runs on the wearable gateway only.

It never leaves the device: it is exported to edge/models/edge_tiny.onnx and is not part of
the AWS deployment. Its job is triage — decide cheaply which 10-second windows are worth
escalating — so it is tuned for high recall; the strong cloud model removes false alarms.

Input: 6 numbers the gateway already has for every window
    hr_mean, hr_range (max-min), rr_cv (SDNN / mean RR), spo2, walking, running
Model: standardise -> Linear(6, 4) -> ReLU -> Linear(4, 1) -> sigmoid   (33 parameters)

Training data: MIT-BIH windows (DS1 patients; label 1 if the window contains any S/V/F beat)
plus simulator windows (healthy and the four abnormal profiles). MIT-BIH has no SpO2 or
activity channel, so those windows get a resting activity and a normal SpO2 drawn from the
healthy range. Test: MIT-BIH DS2 patients + an independent simulator test set.

    python ai-models/training/train_edge_tiny.py --data /path/to/mitdb
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import torch
from torch import nn

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-models" / "preprocessing"))
sys.path.insert(0, str(ROOT / "edge"))
import mitbih  # noqa: E402
from simulator.generator import generate_window  # noqa: E402

OUT = ROOT / "edge" / "models"
FEATURES = ["hr_mean", "hr_range", "rr_cv", "spo2", "walking", "running"]


def feats(hr_mean, hr_min, hr_max, sdnn, spo2, activity):
    rr_mean = 60000.0 / max(hr_mean, 1.0)
    return [hr_mean, hr_max - hr_min, sdnn / rr_mean, spo2, float(activity == "walk"), float(activity == "run")]


def sim_set(n_healthy, n_each, seed):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for prof, n in [("healthy", n_healthy)] + [(p, n_each) for p in ("tachycardia", "bradycardia", "arrhythmia", "hypoxia")]:
        for _ in range(n):
            w = generate_window(prof, rng)
            h = w.hr_stats
            X.append(feats(h["mean"], h["min"], h["max"], h["sdnn"], w.spo2, w.activity))
            y.append(int(w.anomalous))
    return np.array(X, np.float32), np.array(y, np.float32)


def mit_set(ids, data, seed):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for r in ids:
        p = pathlib.Path(data) / str(r)
        if not p.with_suffix(".hea").exists():
            continue
        for w in mitbih.record_windows(p):
            X.append(feats(w["hr_mean"], w["hr_min"], w["hr_max"], w["sdnn"], float(rng.normal(97.8, 0.6)), "rest"))
            y.append(w["label"])
    return np.array(X, np.float32), np.array(y, np.float32)


class Tiny(nn.Module):
    def __init__(self, mean, std):
        super().__init__()
        self.register_buffer("mean", torch.tensor(mean))
        self.register_buffer("std", torch.tensor(std))
        self.net = nn.Sequential(nn.Linear(6, 4), nn.ReLU(), nn.Linear(4, 1))

    def forward(self, x):
        return torch.sigmoid(self.net((x - self.mean) / self.std))


def metrics(p, y, thr):
    pr = p >= thr
    tp = (pr & (y == 1)).sum(); fp = (pr & (y == 0)).sum(); fn = (~pr & (y == 1)).sum()
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return {"n": int(len(y)), "positives": int(y.sum()), "precision": float(prec), "recall": float(rec),
            "f1": float(2 * prec * rec / max(prec + rec, 1e-9)), "false_positive_rate": float(fp / max((y == 0).sum(), 1))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    a = ap.parse_args()
    torch.manual_seed(0)
    val_ids = [106, 119, 208, 223]
    tr_ids = [r for r in mitbih.DS1 if r not in val_ids]
    Xs, ys = sim_set(3000, 600, seed=1)
    Xm, ym = mit_set(tr_ids, a.data, seed=2)
    Xtr, ytr = np.concatenate([Xs, Xm]), np.concatenate([ys, ym])
    Xvs, yvs = sim_set(1000, 200, seed=3)
    Xvm, yvm = mit_set(val_ids, a.data, seed=4)
    Xva, yva = np.concatenate([Xvs, Xvm]), np.concatenate([yvs, yvm])

    model = Tiny(Xtr.mean(0), Xtr.std(0) + 1e-6)
    pos_w = torch.tensor((ytr == 0).sum() / max((ytr == 1).sum(), 1))
    opt = torch.optim.Adam(model.parameters(), lr=0.02)
    X, Y = torch.from_numpy(Xtr), torch.from_numpy(ytr)
    for ep in range(400):
        p = model(X).squeeze(1).clamp(1e-6, 1 - 1e-6)
        loss = -(pos_w * Y * p.log() + (1 - Y) * (1 - p).log()).mean()
        opt.zero_grad(); loss.backward(); opt.step()

    with torch.no_grad():
        pva = model(torch.from_numpy(Xva)).squeeze(1).numpy()
    # Edge is triage: tau_low gives >= 95 % validation recall; tau_high keeps >= 97 % precision.
    cand = np.linspace(0.01, 0.99, 99)
    tau_low = float(max([t for t in cand if metrics(pva, yva, t)["recall"] >= 0.95] or [0.5]))
    tau_high = float(min([t for t in cand if t > tau_low and metrics(pva, yva, t)["precision"] >= 0.97] or [0.98]))

    Xts, yts = sim_set(1000, 200, seed=5)
    Xtm, ytm = mit_set(mitbih.DS2, a.data, seed=6)
    with torch.no_grad():
        pts = model(torch.from_numpy(Xts)).squeeze(1).numpy()
        ptm = model(torch.from_numpy(Xtm)).squeeze(1).numpy() if len(Xtm) else np.zeros(0)
    test = {"simulator": metrics(pts, yts, tau_low), "mitbih_DS2": metrics(ptm, ytm, tau_low) if len(ytm) else None}

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "edge_tiny.onnx"
    torch.onnx.export(model, torch.zeros(1, 6), str(path), input_names=["features"], output_names=["p_abnormal"],
                      dynamic_axes={"features": {0: "n"}, "p_abnormal": {0: "n"}}, opset_version=17, dynamo=False)
    meta = {"model": "edge_tiny", "version": "edge-tiny-1.0.0", "features": FEATURES,
            "parameters": int(sum(p.numel() for p in model.net.parameters())), "onnx_bytes": path.stat().st_size,
            "thresholds": {"tau_low": tau_low, "tau_high": tau_high},
            "training": {"simulator_windows": int(len(ys)), "mitbih_windows": int(len(ym)), "mitbih_records": tr_ids},
            "test_metrics_at_tau_low": test, "deployment": "edge only - not uploaded to AWS"}
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
