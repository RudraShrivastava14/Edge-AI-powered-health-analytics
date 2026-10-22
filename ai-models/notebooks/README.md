# Notebooks

Exploration and reported experiments. Notebooks are for *investigation*; anything that
produces a reported number belongs in a script under `training/` so it is reproducible.

| Notebook | Purpose |
|---|---|
| `00_data_exploration.ipynb` | Signal quality, class balance, subject demographics, artefact survey |
| `01_baselines.ipynb` | Threshold rules, Isolation Forest, one-class SVM |
| `02_autoencoder.ipynb` | Architecture search, bottleneck width, threshold selection |
| `03_quantisation.ipynb` | FP32 vs INT8, latency on Pi, accuracy delta |
| `04_cascade_analysis.ipynb` | Two-stage confusion matrix, recall-vs-uplink operating curve |

## Rules

- **Clear all outputs before committing** (`jupyter nbconvert --clear-output --inplace`) —
  otherwise diffs are unreadable and the repo bloats with embedded images.
- Fix the seed in the first cell.
- Notebooks read from `dataset/processed/`; they never write there.
- Export final figures to `results/figures/` with the generating code preserved.
