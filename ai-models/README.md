# AI Models

Model development, from raw physiological signals to a deployable INT8 TFLite artefact.
Owner: **Monis Raza (MR)**.

## The two models

| | **Edge model** | **Cloud model** |
|---|---|---|
| Purpose | Cheap screening of every window | Confirmation of escalated windows only |
| Architecture | 1-D convolutional autoencoder, 4 conv blocks | Wider autoencoder + a supervised classifier head for anomaly class |
| Input | 10 s × 125 Hz single-lead ECG + HR/SpO₂/temp/activity features | Same window at full precision |
| Size | **< 500 KB**, INT8 quantised | ~10–20 MB, FP32, loaded from S3 |
| Runs on | Raspberry Pi CPU / TFLite runtime | AWS Lambda (512 MB) |
| Optimised for | Latency (< 50 ms) and **recall** — false positives are acceptable, false negatives are not | **Precision** — it exists to reject the edge's false positives |

The cascade is the project's core idea: the edge is deliberately over-sensitive, and the
cloud stage cleans up. Report the two-stage confusion matrix, not just each model alone.

## Why an autoencoder

Labelled abnormal wearable data is scarce; normal data is abundant. Training a
reconstruction model on normal windows only, and thresholding reconstruction error, is a
semi-supervised formulation that needs no anomaly labels at training time (see
[`docs/literature-survey/`](../docs/literature-survey/LITERATURE_SURVEY.md), refs [11][12]).
Supervised baselines are still trained for comparison, since MIT-BIH *is* labelled.

## Pipeline

```
raw dataset → preprocessing/ → windows (.npy) → training/ → .keras → quantize.py → .tflite → edge/
                                                                  └→ S3 (cloud model)
```

## Layout

```
ai-models/
├── preprocessing/    dataset download, filtering, resampling, windowing, train/val/test split
├── notebooks/        exploration and reported experiments (clear outputs before committing)
├── training/         train_autoencoder.py, train_classifier.py, quantize.py, evaluate.py
└── models/           artefacts — small files only; large weights go to S3 (see below)
```

## Experiment protocol

- **Subject-wise splits**, never window-wise — otherwise windows from the same recording
  leak between train and test and the reported accuracy is meaningless.
- Fixed seeds; log every run's config and metrics to `results/benchmarks/`.
- Report **precision, recall, F1, ROC-AUC, PR-AUC**. With ~1 % anomaly prevalence, accuracy
  is a useless metric — say so in the report.
- The threshold τ is chosen on the **validation** set at a fixed false-negative budget
  (target ≤ 5 %), then frozen before touching the test set.
- Quantisation is evaluated as a first-class result: report the FP32 → INT8 metric delta.

## Model artefacts

`models/` is for small committed artefacts (< 10 MB) and metadata only. Anything larger
lives in S3 under `models/` in the raw-data bucket and is referenced by version:

```
models/
├── edge/autoencoder_int8.tflite      # committed if < 10 MB
├── cloud/MODEL_CARD.md               # metadata; weights in S3
└── VERSIONS.md                       # version → training run → metrics → S3 key
```

Model version strings (e.g. `ae-int8-1.2.0`) appear in every telemetry payload, so any
prediction can be traced back to the exact model that made it.

## TODO

- [ ] M-1 Download scripts for MIT-BIH, PTB-XL, WESAD
- [ ] M-2 Preprocessing: 0.5–40 Hz bandpass, resample to 125 Hz, per-record z-normalisation, 10 s windows @ 50 % overlap
- [ ] M-3 Baselines: fixed thresholds, Isolation Forest, one-class SVM
- [ ] M-4 Conv autoencoder + threshold selection
- [ ] M-5 INT8 post-training quantisation with a representative dataset; verify Δaccuracy < 2 %
- [ ] M-7 Cloud confirmation model + Lambda packaging
- [ ] M-8 Evaluation report and figures → `results/`
