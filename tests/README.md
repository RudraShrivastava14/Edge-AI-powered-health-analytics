# Tests

Shared ownership; each member tests what they build.

## Layout

```
tests/
├── unit/          pure logic, no network, no AWS — must run in < 10 s
├── integration/   AWS interactions, mocked with `moto` by default
└── requirements.txt
```

## Running

```bash
pip install -r tests/requirements.txt
pytest tests/unit -q                  # fast, run on every save
pytest tests/integration -q           # moto-mocked, no real AWS calls, no cost
pytest tests/integration -q --live    # hits the deployed dev stack — consumes quota
pytest --cov=backend --cov=edge tests/
```

## What to cover

### Unit
- Telemetry JSON-schema validation: valid, missing required field, wrong type, extra field
- Uplink policy thresholds: exact boundary values at `τ_low` and `τ_high`
- DynamoDB key construction and the ordering property of `TS#<millis>#<seq>` sort keys
- Alert deduplication/debounce window logic
- Unit normalisation (°F → °C, bpm bounds)
- Buffer eviction when the ring is full — critical windows must survive, normal ones evict first

### Integration (moto)
- `ingest_handler` given an IoT event writes the expected DynamoDB item
- A `critical` message archives to S3 **and** invokes `anomaly_processor`
- A malformed payload lands in `quarantine/` and does **not** raise
- `api_handler` returns 401 without a JWT, 403 for a device the caller does not own
- Alert acknowledgement updates `status` and populates the ack fields

### Live (`--live`, run sparingly)
- End-to-end: publish over MQTT → assert a DynamoDB item appears within N seconds
- SNS delivery reaches a test subscription
- Latency measurement harness used for benchmark E4

## Conventions

- `pytest` + `moto` for AWS mocks; `freezegun` for time-dependent logic
- No test may create a real AWS resource unless it is marked `@pytest.mark.live`
- Deterministic tests: fix seeds, freeze the clock, no `sleep` polling without a timeout
- Fixtures for sample payloads live in `tests/fixtures/` and are shared with
  `backend/events/` so SAM local and pytest exercise identical inputs

## CI

`.github/workflows/ci.yml` runs `pytest tests/unit tests/integration` on every push and PR.
Live tests are **not** run in CI — they cost quota and need credentials.

## TODO

- [ ] `conftest.py` with shared fixtures (moto-backed tables, sample events)
- [ ] Unit suites per module above
- [ ] Integration suites per Lambda
- [ ] `load_test.py` — N concurrent simulated devices, for benchmark E6
