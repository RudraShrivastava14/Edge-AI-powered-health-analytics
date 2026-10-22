# Preprocessing

Turns raw dataset files into the uniform window format defined in
[`dataset/README.md` §3](../../dataset/README.md#3-preprocessing-contract).

| Script | Purpose | Status |
|---|---|---|
| `download.py` | Fetch MIT-BIH / PTB-XL / WESAD into `dataset/raw/`, verify checksums | TODO (M-1) |
| `signal_ops.py` | Butterworth bandpass 0.5–40 Hz (zero-phase), resample to 125 Hz, per-record z-score | TODO (M-2) |
| `prepare_mitbih.py` | MIT-BIH → windows + labels + feature table | TODO (M-2) |
| `prepare_ptbxl.py` | PTB-XL → same format | TODO (M-2) |
| `prepare_wesad.py` | WESAD → same format, plus wrist-vs-chest comparison | TODO (M-2) |
| `augment.py` | Inject baseline wander, powerline hum, motion artefacts — makes clinical-grade data look wearable-grade | TODO (M-2) |

## Non-negotiables

- **Subject-disjoint splits.** Splitting by window leaks recordings across train and test and
  inflates every metric. This is the single easiest way to produce a meaningless result.
- **Normalise per record**, using only that record's statistics — never corpus-wide, which
  leaks test information into training.
- **Never modify `dataset/raw/`.** Every transformation reads raw and writes processed.
- Write a `manifest.json` with the config hash, split assignment, and per-file checksums so
  any result can be traced to the exact data that produced it.
