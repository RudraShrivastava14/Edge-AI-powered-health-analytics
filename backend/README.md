# Backend Tier — Serverless Services

All cloud-side compute. Owner: **Krish Agarwal (KA)**.

Every unit here is an **AWS Lambda function** — there are no always-on servers, which is
what keeps the project inside the perpetual Free Tier.

## Functions

| Function | Trigger | Responsibility | Memory / Timeout |
|---|---|---|---|
| `ingest_handler` | IoT Core Rule on `hh/v1/+/telemetry` | Validate against the JSON schema, normalise units, write the summary to DynamoDB, archive any attached raw window to S3, escalate `suspect`/`critical` to the processor | 256 MB / 10 s |
| `anomaly_processor` | Async invoke from `ingest_handler` | Run the full-precision confirmation model on the raw window, cross-check with rule-based limits, write an Alert or record a hard negative | 512 MB / 30 s |
| `alert_dispatcher` | Async invoke from `anomaly_processor` | Deduplicate and debounce (max 1 notification per device per class per 5 min), format and publish to SNS | 128 MB / 10 s |
| `api_handler` | API Gateway HTTP API (JWT-authorised) | Serve `/v1/devices`, `/v1/…/vitals`, `/v1/alerts`, alert acknowledgement | 256 MB / 10 s |

## Layout

```
backend/
├── lambdas/
│   ├── ingest_handler/       app.py, requirements.txt
│   ├── anomaly_processor/
│   ├── alert_dispatcher/
│   └── api_handler/
├── common/                   shared layer: schema validation, DDB helpers, logging, config
└── api/                      OpenAPI spec + route → handler mapping
```

`common/` is packaged as a **Lambda layer** so the four functions share one copy of the
validation and persistence helpers.

## Conventions

- **Structured JSON logging** with `requestId`, `deviceId`, and duration on every line.
  Never log payload bodies — it burns the CloudWatch free tier and risks leaking data.
- **Idempotency:** `(deviceId, ts, seq)` is the natural key; a replayed message overwrites
  rather than duplicating.
- **Never raise on bad input.** Malformed messages go to the `quarantine/` S3 prefix, emit a
  CloudWatch metric, and return success so IoT Core does not retry forever.
- **Async invocations get a dead-letter queue** so failures are inspectable.
- **Cold starts matter** for the < 5 s latency target: keep deployment packages small, do
  heavy imports lazily, and load the model outside the handler so it survives across warm
  invocations.

## Local development

```bash
pip install -r requirements-dev.txt
sam local invoke IngestFunction -e events/telemetry_normal.json
sam local start-api                  # exercise api_handler on http://localhost:3000
pytest ../tests/unit -q
```

## TODO

- [ ] B-1 JSON Schema in `common/schemas/telemetry.v1.json` + validator
- [ ] B-2 `ingest_handler`
- [ ] B-3 `anomaly_processor` (model loaded from S3 into `/tmp`, cached across invocations)
- [ ] B-4 `alert_dispatcher` with debounce state in DynamoDB
- [ ] B-5 `api_handler` + OpenAPI spec in `api/openapi.yaml`
- [ ] B-7 Cognito JWT authorizer wiring + per-device authorisation check
- [ ] Sample event fixtures in `events/`
