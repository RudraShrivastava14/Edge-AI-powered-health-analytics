# Edge model — training report

**Model:** 1-D convolutional autoencoder (`ecg_autoencoder.onnx`, ae-onnx-1.0.0)
**Parameters:** 31,137 · **ONNX size:** 125 KB (target < 500 KB) · **CPU inference:** 0.68 ms/window
**Input:** single-lead ECG, 125 Hz, first 1,248 samples of a 10 s window, per-window z-score
**Score:** mean squared reconstruction error. Trained on healthy windows only (semi-supervised).
**Data:** synthetic windows from `edge/simulator` — 4,000 train / 1,000 validation (healthy), independent test set per profile. Not yet trained on MIT-BIH.
**ONNX vs PyTorch max difference:** 2.4e-06

## Test results (held-out)

Healthy false-positive rate: **1.7 %** (n = 1000)

| Profile | n | Recall | ROC-AUC |
|---|---|---|---|
| tachycardia | 500 | 100 % | 1.000 |
| bradycardia | 500 | 91 % | 0.972 |
| arrhythmia | 500 | 99 % | 0.923 |
| hypoxia | 500 | 71 % | 0.750 |

**Overall:** precision 0.991 · recall 0.902 · F1 0.945 · ROC-AUC 0.911

Hypoxia is weakest because low SpO₂ is not visible in the ECG; the edge therefore pairs the model with a
rule-based SpO₂ guard (suspect < 93 %, critical < 90 %), and the cloud stage re-checks SpO₂ as well.

## Thresholds (from the healthy validation set, per activity)

| Activity | τ_low (99th pct) | τ_high |
|---|---|---|
| rest | 0.0279 | 0.0482 |
| walk | 0.0555 | 0.0869 |
| run | 0.0938 | 0.1439 |

Reproduce: `python ai-models/training/train_autoencoder.py`
