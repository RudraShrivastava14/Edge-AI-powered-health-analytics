# Seed Data

Deterministic sample data for local development, demos, and integration tests.

| File | Purpose | Status |
|---|---|---|
| `devices.json` | 5 sample devices with labels and owners | TODO (B-6b) |
| `telemetry_sample.json` | ~1 h of summaries for one device, including one anomaly episode | TODO (B-6b) |
| `alerts_sample.json` | A few alerts across severities and statuses | TODO (B-6b) |
| `load.py` | `boto3` loader targeting the dev stack or DynamoDB Local | TODO (B-6b) |

```bash
python seed/load.py --stack health-analytics-dev
python seed/load.py --local        # DynamoDB Local on :8000
```

Seed data must be **synthetic** — never derived from a real person, and never a real
patient record even if de-identified.
