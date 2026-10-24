# Models

Two trained models split the work, as the architecture intends: a tiny one on the edge for
triage, a strong one in the cloud for confirmation.

| | Edge model (tiny) | Cloud model (strong) |
|---|---|---|
| File | `edge/models/edge_tiny.onnx` | `ai-models/models/cloud_beat_classifier.onnx` (copied into the `anomaly_processor` Lambda) |
| Where it runs | Gateway / Mac only — **never uploaded to AWS** | AWS Lambda, only for escalated windows |
| Architecture | standardise → Linear(6,4) → ReLU → Linear(4,1) → sigmoid | 2-channel 1-D CNN (beat + patient's local template) fused with an RR-timing MLP |
| Size | 33 parameters, 914 bytes | 50.7 k parameters, 200 KB |
| Input | per window: HR mean, HR range, RR irregularity, SpO₂, walking, running | per beat: 96 ECG samples (0.77 s) + 5 RR timing features |
| Output | P(window abnormal) → normal / suspect / critical | per beat: N (normal), S (supraventricular ectopic), V (ventricular ectopic) |
| Speed | ~0.2 ms / window | ~15–50 ms / window (warm Lambda) |
| Training script | `ai-models/training/train_edge_tiny.py` | `ai-models/training/train_cloud_classifier.py` |

## Dataset

**MIT-BIH Arrhythmia Database** — 48 half-hour two-lead ambulatory ECGs from 47 patients,
~110,000 beats annotated by cardiologists. License: Open Data Commons Attribution v1.0.

- Original: https://physionet.org/content/mitdb/1.0.0/
- AWS Open Data mirror (used here): https://registry.opendata.aws/physionet/ — `s3://physionet-open/mitdb/1.0.0/`
- Moody & Mark (2001), *IEEE Eng. Med. Biol. Mag.* 20(3):45–50; Goldberger et al. (2000), *Circulation* 101(23):e215.

Preprocessing (`ai-models/preprocessing/mitbih.py`): MLII lead, Butterworth band-pass
0.5–40 Hz, resampled 360 → 125 Hz, AAMI beat classes (F merged into V; paced records
102/104/107/217 excluded).

**Split — inter-patient (de Chazal et al., 2004):** train on 22 DS1 patients, test on 22
different DS2 patients. No patient appears in both, so results reflect performance on people
the model has never seen.

The edge model additionally uses simulator windows, because MIT-BIH has no SpO₂ or
activity channel (MIT-BIH windows get a resting activity and a normal SpO₂).

## Results (unseen DS2 patients)

**Cloud model, per beat** (49,684 beats): accuracy **90.4 %**

| Class | Sensitivity | Precision |
|---|---|---|
| N normal | 93.4 % | 97.7 % |
| V ventricular ectopic | 91.9 % | 50.9 % |
| S supraventricular ectopic | 16.9 % | 34.9 % |

**Cloud model, per 10-second window** (the confirm / reject decision; confirm if any beat has
P(S)+P(V) ≥ 0.9), 3,960 windows: precision **0.82**, recall **0.90**, F1 **0.86**,
specificity 0.88. Through the full Lambda path (own R-peak detector + numpy filter instead of
cardiologist annotations): F1 **0.82**.

**Edge model, per window** (tuned for recall — it is the triage stage):
MIT-BIH DS2 recall **0.90**, precision 0.79, F1 0.84; simulator test F1 0.99.

## Limitations (stated honestly)

- S beats are the weakest class: they look normal and differ only in timing; inter-patient S
  detection is a known hard problem in this literature.
- MIT-BIH is clinical-electrode ECG from 47 patients; wrist-wearable ECG is noisier.
- Tachycardia, bradycardia and desaturation are confirmed by explicit rules on the
  waveform-measured heart rate and SpO₂, not by the CNN, which classifies beat type.
- Not a medical device; no clinical validation.

## Other model

`ai-models/models/ecg_autoencoder.onnx` — the earlier 1-D convolutional autoencoder
(31 k params, reconstruction-error scoring, trained on simulator windows). Still selectable
with `--scorer autoencoder`.

## Reproduce

```bash
aws s3 cp --no-sign-request --recursive s3://physionet-open/mitdb/1.0.0/ data/mitdb
python ai-models/training/train_edge_tiny.py        --data data/mitdb
python ai-models/training/train_cloud_classifier.py --data data/mitdb
python ai-models/preprocessing/export_replay.py     --data data/mitdb --records 100 119 208 233
```
