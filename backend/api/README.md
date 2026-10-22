# API Definition

| File | Purpose |
|---|---|
| `openapi.yaml` | OpenAPI 3.1 spec — the contract of record for the REST API (TODO, B-5) |

The spec is the source of truth: import it into API Gateway, generate the frontend client
from it, and validate responses against it in integration tests. If the spec and the code
disagree, the spec is wrong until fixed — do not let them drift.

Human-readable version with examples:
[`docs/architecture/API_CONTRACT.md`](../../docs/architecture/API_CONTRACT.md).
