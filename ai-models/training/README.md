# Training

| Script | Purpose | Status |
|---|---|---|
| `train_autoencoder.py` | 1-D conv autoencoder on **normal windows only**; semi-supervised anomaly detection | TODO (M-4) |
| `train_classifier.py` | Supervised anomaly-class head for the cloud confirmation model | TODO (M-7) |
| `select_threshold.py` | Pick τ_low/τ_high on validation at a fixed false-negative budget | TODO (M-4) |
| `quantize.py` | Post-training INT8 quantisation → TFLite, with a representative dataset | TODO (M-5) |
| `evaluate.py` | Metrics, confusion matrices, PR/ROC curves, the two-stage cascade matrix | TODO (M-8) |
| `baselines.py` | Fixed thresholds, Isolation Forest, one-class SVM | TODO (M-3) |

## Architecture sketch (edge autoencoder)

```
Input (1250, 1)
  Conv1D 16 k=7 s=2 + BN + ReLU      → (625, 16)
  Conv1D 32 k=5 s=2 + BN + ReLU      → (313, 32)
  Conv1D 64 k=5 s=2 + BN + ReLU      → (157, 64)
  Conv1D 32 k=3 s=2 + BN + ReLU      → ( 79, 32)   ← bottleneck
  Conv1DTranspose ×4 (mirror)        → (1250, 1)
Loss: MSE   Optimiser: Adam 1e-3, cosine decay   Early stopping on val loss
```

Keep the bottleneck tight — an autoencoder that reconstructs *everything* well, including
anomalies, detects nothing. If val reconstruction error is near-identical for normal and
abnormal windows, the bottleneck is too wide.

## Reproducibility

Every run writes to `results/benchmarks/runs/<timestamp>/` : config, seed, git commit,
metrics, and the model hash. A number in the report with no run directory behind it is not
a result.
