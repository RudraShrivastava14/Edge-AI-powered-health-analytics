# Model Artefacts

Small artefacts (< 10 MB) and metadata are committed. Larger weights live in S3 under
`s3://<raw-bucket>/models/` and are referenced by version.

```
models/
├── edge/    autoencoder_int8.tflite  (target < 500 KB — committed)
├── cloud/   MODEL_CARD.md            (weights in S3)
└── VERSIONS.md
```

## `VERSIONS.md` format

| Version | Date | Trained on | Test PR-AUC | Recall @ τ | Size | Artefact |
|---|---|---|---|---|---|---|
| `ae-int8-1.0.0` | | MIT-BIH train split | | | | `edge/autoencoder_int8.tflite` |

The version string is embedded in every telemetry payload (`edge.modelVersion`), so any
prediction in the database can be traced to the exact model that made it. Never overwrite a
released version — bump it.

## Model card (required for the report)

Each model needs: intended use, training data and its limitations, evaluation results with
the operating point, known failure modes (motion artefacts, unseen arrhythmia classes,
demographic coverage), and an explicit statement that it is **not** clinically validated.
