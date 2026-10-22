# Integration Tests

AWS interactions, **mocked with `moto` by default** — no real resources, no cost.

| Suite | Covers |
|---|---|
| `test_ingest.py` | IoT event → expected DynamoDB item; raw window archived to S3; `critical` triggers the processor invoke |
| `test_quarantine.py` | Malformed payload lands in `quarantine/`, emits a metric, does **not** raise |
| `test_api_auth.py` | 401 without a JWT; **403 for a device the caller does not own** (the highest-risk bug in the project) |
| `test_api_query.py` | Range queries, pagination cursors, server-side `limit` cap |
| `test_alerts.py` | Alert creation, dedupe, SNS publish, acknowledgement |
| `load_test.py` | N concurrent simulated devices — benchmark E6 |

## Live mode

```bash
pytest tests/integration -q --live   # hits the deployed dev stack; consumes free-tier quota
```

Tests requiring real AWS are marked `@pytest.mark.live` and are **excluded from CI**. Run
them deliberately, and tear the stack down afterwards.
