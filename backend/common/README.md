# `common` — Shared Lambda Layer

Packaged as a Lambda layer so all four functions share one copy.

| Module | Purpose |
|---|---|
| `schema.py` | Load and validate `hh.telemetry.v1`; raise `ValidationError` with a field path |
| `schemas/telemetry.v1.json` | The JSON Schema itself (machine-readable form of the API contract) |
| `ddb.py` | Key construction (`DEV#`, `TS#`, `ALERT#`), item (de)serialisation, cursor encode/decode |
| `s3.py` | Raw-window archival paths, gzip encode/decode |
| `logging.py` | Structured JSON logger with `requestId` / `deviceId` correlation |
| `config.py` | Environment + SSM Parameter Store configuration loader with caching |
| `errors.py` | RFC 7807 problem-detail helpers |

## Rules
- **No AWS SDK calls at import time** — it slows every cold start.
- Keep the layer small; large dependencies belong in the one function that needs them.
- Anything used by two or more functions belongs here, not copy-pasted.
