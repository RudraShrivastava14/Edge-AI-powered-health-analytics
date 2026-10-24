"""Cloud model: 1-D CNN heartbeat classifier (AAMI N / S / V / F) trained on MIT-BIH.

Runs in AWS Lambda (anomaly_processor) on escalated windows only. Each beat in the window is
classified from (a) its ECG shape and (b) its timing (RR features); the window is confirmed
when the beat classes say so.

Evaluation is inter-patient (de Chazal DS1 -> DS2): the test patients are never seen in
training, which is the honest setting and markedly harder than random beat splits.

    python ai-models/training/train_cloud_classifier.py --data /path/to/mitdb
Outputs ai-models/models/cloud_beat_classifier.{onnx,json}
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np
import torch
from torch import nn

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-models" / "preprocessing"))
import mitbih  # noqa: E402

OUT = ROOT / "ai-models" / "models"


class BeatNet(nn.Module):
    """Shape branch (1-D CNN) + timing branch (RR MLP), fused."""

    def __init__(self, n_classes=3):
        super().__init__()
        self.shape = nn.Sequential(
            nn.Conv1d(2, 32, 7, padding=3), nn.BatchNorm1d(32), nn.ReLU(), nn.MaxPool1d(2),
            nn.Conv1d(32, 64, 5, padding=2), nn.BatchNorm1d(64), nn.ReLU(), nn.MaxPool1d(2),
            nn.Conv1d(64, 64, 5, padding=2), nn.BatchNorm1d(64), nn.ReLU(), nn.MaxPool1d(2),
            nn.Conv1d(64, 64, 3, padding=1), nn.BatchNorm1d(64), nn.ReLU(),
            nn.AdaptiveAvgPool1d(1), nn.Flatten(),
        )
        self.timing = nn.Sequential(nn.Linear(mitbih.N_RR, 32), nn.ReLU())
        self.head = nn.Sequential(nn.Dropout(0.3), nn.Linear(96, 64), nn.ReLU(), nn.Linear(64, n_classes))

    def forward(self, beat, rr):
        return self.head(torch.cat([self.shape(beat), self.timing(rr)], dim=1))


def load(ids, data):
    xs, rs, ys, rec = [], [], [], []
    for r in ids:
        p = pathlib.Path(data) / str(r)
        if not p.with_suffix(".hea").exists():
            print(f"  missing record {r}, skipped")
            continue
        s, rr, y = mitbih.record_beats(p)
        xs.append(s); rs.append(rr); ys.append(y); rec += [r] * len(y)
    return np.concatenate(xs), np.concatenate(rs), np.concatenate(ys), np.array(rec)


def report(y, pred, k=3):
    cm = np.zeros((k, k), dtype=int)
    for t, p in zip(y, pred):
        cm[t, p] += 1
    per = {}
    for i, c in enumerate(mitbih.CLASSES):
        tp = cm[i, i]; fn = cm[i].sum() - tp; fp = cm[:, i].sum() - tp
        per[c] = {"n": int(cm[i].sum()), "sensitivity": float(tp / max(tp + fn, 1)),
                  "ppv": float(tp / max(tp + fp, 1))}
    # Clinically relevant binary view: abnormal (S/V/F) vs normal.
    ab_t, ab_p = y != 0, pred != 0
    tp = (ab_t & ab_p).sum(); fp = (~ab_t & ab_p).sum(); fn = (ab_t & ~ab_p).sum()
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return {"confusion_matrix": cm.tolist(), "per_class": per, "accuracy": float(np.trace(cm) / cm.sum()),
            "abnormal_vs_normal": {"precision": float(prec), "recall": float(rec),
                                   "f1": float(2 * prec * rec / max(prec + rec, 1e-9))}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--epochs", type=int, default=12)
    a = ap.parse_args()
    torch.manual_seed(0); np.random.seed(0)
    t0 = time.time()
    xtr, rtr, ytr, rec_tr = load(mitbih.DS1, a.data)
    xte, rte, yte, _ = load(mitbih.DS2, a.data)
    # All DS1 patients train with a fixed schedule (no early stopping): holding out DS1
    # records removed nearly all fusion/ventricular examples in an earlier run.
    vm = np.zeros(len(ytr), dtype=bool)
    print("train", np.bincount(ytr, minlength=3), "test", np.bincount(yte, minlength=3), flush=True)

    model = BeatNet()
    counts = np.bincount(ytr[~vm], minlength=3).astype(float)
    w = torch.tensor((counts.sum() / np.maximum(counts, 1)) ** 0.5, dtype=torch.float32)
    loss_fn = nn.CrossEntropyLoss(weight=w / w.mean())
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    X, R, Y = map(torch.from_numpy, (xtr[~vm], rtr[~vm], ytr[~vm]))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-3, total_steps=a.epochs * ((len(X) + 255) // 256))

    def predict(x, r):
        model.eval()
        with torch.no_grad():
            return torch.cat([model(x[i:i + 2048], r[i:i + 2048]) for i in range(0, len(x), 2048)]).softmax(1)

    for ep in range(a.epochs):
        model.train()
        perm = torch.randperm(len(X))
        for i in range(0, len(X), 256):
            idx = perm[i:i + 256]
            xb = X[idx] + 0.05 * torch.randn_like(X[idx])  # noise augmentation
            loss = loss_fn(model(xb, R[idx]), Y[idx])
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        print(f"epoch {ep+1:2d} loss {loss.item():.4f}", flush=True)

    probs = predict(torch.from_numpy(xte), torch.from_numpy(rte)).numpy()
    test = report(yte, probs.argmax(1))
    print(json.dumps({k: test[k] for k in ("accuracy", "abnormal_vs_normal")}, indent=1))
    print(json.dumps(test["per_class"], indent=1))

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "cloud_beat_classifier.onnx"

    class Export(nn.Module):  # softmax baked in
        def __init__(self, m):
            super().__init__(); self.m = m

        def forward(self, beat, rr):
            return self.m(beat, rr).softmax(1)

    model.eval()
    torch.onnx.export(Export(model), (torch.zeros(1, 2, mitbih.BEAT_LEN), torch.zeros(1, mitbih.N_RR)), str(path),
                      input_names=["beat", "rr"], output_names=["probs"],
                      dynamic_axes={"beat": {0: "n"}, "rr": {0: "n"}, "probs": {0: "n"}}, opset_version=17, dynamo=False)
    meta = {"model": "cloud_beat_classifier", "version": "beatcnn-1.0.0", "classes": mitbih.CLASSES,
            "parameters": int(sum(p.numel() for p in model.parameters())), "onnx_bytes": path.stat().st_size,
            "input": {"beat": f"[2, {mitbih.BEAT_LEN}] at 125 Hz ({mitbih.BEAT_BEFORE} before R), per-beat z-score; ch0 beat, ch1 median of +-8 neighbouring beats",
                      "rr": "pre-RR, post-RR, local median RR (9 beats), pre/local, post/pre"},
            "dataset": "MIT-BIH Arrhythmia Database (PhysioNet), MLII, 0.5-40 Hz, 125 Hz, AAMI classes",
            "split": "inter-patient: train all DS1 patients, test DS2 patients (de Chazal 2004)",
            "test_metrics": test, "train_seconds": round(time.time() - t0, 1)}
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    print("saved", path, meta["onnx_bytes"], "bytes")


if __name__ == "__main__":
    main()
