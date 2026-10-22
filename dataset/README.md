# Datasets

> **Raw data is NOT committed to this repository.** It is large, and some sources have
> licence terms that require attribution and prohibit redistribution. Download it locally
> with the scripts in [`ai-models/preprocessing/`](../ai-models/preprocessing/); the
> `data/` directory is gitignored.

Owner: **Monis Raza (MR)**.

---

## 1. Datasets Used

### MIT-BIH Arrhythmia Database *(primary)*
- **Source:** PhysioNet — <https://physionet.org/content/mitdb/1.0.0/>
- **Contents:** 48 half-hour excerpts, two-channel ambulatory ECG, 360 Hz, 11-bit, from 47
  subjects; beat-by-beat cardiologist annotations (~110 000 beats).
- **Licence:** Open Data Commons Attribution License v1.0.
- **Used for:** training the autoencoder on normal beats; evaluating anomaly detection
  against the beat annotations.
- **Size:** ~100 MB.

### PTB-XL
- **Source:** PhysioNet — <https://physionet.org/content/ptb-xl/>
- **Contents:** 21 837 clinical 12-lead ECGs, 10 s each, 100 Hz and 500 Hz versions,
  18 885 patients, multi-label diagnostic statements.
- **Licence:** Creative Commons Attribution 4.0.
- **Used for:** generalisation check — does a model trained on MIT-BIH transfer?
- **Size:** ~2 GB (100 Hz version ~1.7 GB).

### WESAD
- **Source:** UCI ML Repository — <https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detection>
- **Contents:** 15 subjects; chest device (ECG, EDA, EMG, TEMP, RESP, ACC @ 700 Hz) and
  wrist device (BVP, EDA, TEMP, ACC); baseline / stress / amusement labels.
- **Licence:** research use, cite the paper.
- **Used for:** realistic *wearable-grade* (noisier) signals and multimodal fusion.
- **Size:** ~18 GB.

### MHEALTH
- **Source:** UCI ML Repository — <https://archive.ics.uci.edu/dataset/319/mhealth+dataset>
- **Contents:** 10 subjects, 23 channels (acceleration, gyro, magnetometer, 2-lead ECG),
  12 physical activities.
- **Used for:** activity-context labels, so the detector can distinguish "HR 160 while
  running" from "HR 160 at rest" (RQ5).
- **Size:** ~1 GB.

### Synthetic stream *(generated, in-repo)*
- **Source:** [`edge/simulator/`](../edge/simulator/)
- **Used for:** load testing, the elasticity demo, and the live viva demo — no dataset
  download needed to see the system work end to end.

---

## 2. Directory Convention (gitignored)

```
dataset/
├── README.md            ← committed
├── DATA_CARD.md         ← committed
├── raw/                 ← gitignored: exactly as downloaded, never modified
│   ├── mitdb/
│   ├── ptbxl/
│   └── wesad/
└── processed/           ← gitignored: outputs of the preprocessing pipeline
    ├── train/ val/ test/       (subject-disjoint splits)
    └── manifest.json           (checksums, split assignment, preprocessing config)
```

Rule: **`raw/` is immutable.** Every transformation is a script that reads `raw/` and writes
`processed/`, so any result can be regenerated from scratch.

---

## 3. Preprocessing Contract

Every dataset is normalised to the same window format before training:

| Property | Value |
|---|---|
| Signal | Single-lead ECG (lead II or nearest equivalent) |
| Filter | Butterworth bandpass, 0.5–40 Hz, zero-phase (`filtfilt`) |
| Resample | 125 Hz |
| Window | 10 s (1 250 samples), 50 % overlap |
| Normalisation | Per-record z-score (fit on that record only — never on the whole corpus) |
| Auxiliary features | HR mean/min/max, SDNN, SpO₂ (where available), temperature, activity class |
| Label | `0` = normal, `1` = anomalous (any non-normal annotated beat within the window) |
| Split | **Subject-disjoint** 70 / 15 / 15 — no subject appears in two splits |

Output: `X` of shape `(n_windows, 1250, 1)` float32, `y` of shape `(n_windows,)` int8, plus
a feature table, saved as compressed `.npz` with a `manifest.json` recording the config hash.

---

## 4. Download

```bash
cd ai-models
python preprocessing/download.py --dataset mitdb --out ../dataset/raw
python preprocessing/prepare_mitbih.py --raw ../dataset/raw/mitdb --out ../dataset/processed
```

MIT-BIH and PTB-XL can also be fetched with the PhysioNet CLI:

```bash
wget -r -N -c -np https://physionet.org/files/mitdb/1.0.0/
```

---

## 5. Ethics & Privacy

- All datasets are **publicly released and de-identified**; no institutional ethics approval
  is required for their secondary use, and this project collects **no new human data**.
- Cite the dataset papers in the final report (BibTeX entries are in
  [`docs/literature-survey/references.bib`](../docs/literature-survey/references.bib)).
- The deployed system stores **no PII**: device IDs are opaque identifiers, and any mapping
  to a person lives outside this system.
- Redistribution of the raw data through this repository is not permitted — hence the
  gitignore.

---

## 6. Known Limitations (state these in the report)

- MIT-BIH was recorded with **clinical electrodes**, not a wrist wearable; real PPG-derived
  signals are considerably noisier. We mitigate with noise/motion-artefact augmentation and
  cross-check on WESAD's wrist data, but this remains a threat to external validity.
- MIT-BIH has only 47 subjects — limited demographic diversity.
- Anomaly prevalence in the curated datasets is far higher than in a free-living population,
  so the reported precision is optimistic relative to real deployment.
