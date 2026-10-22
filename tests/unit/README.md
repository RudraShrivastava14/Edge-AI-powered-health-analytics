# Unit Tests

Pure logic. **No network, no AWS, no filesystem beyond `tmp_path`.** The whole suite must
run in under 10 seconds so it can be run on every save.

| Suite | Covers |
|---|---|
| `test_schema.py` | Telemetry validation: valid, missing field, wrong type, out-of-range vital, `raw` present on a `normal` flag (must fail) |
| `test_policy.py` | `classify()` at exact `τ_low` / `τ_high` boundaries; activity scaling; payload construction |
| `test_encoding.py` | `encode_window` round-trip; downsampling; size bounds |
| `test_ddb_keys.py` | Key construction; lexicographic ordering of `TS#<millis>#<seq>` sort keys |
| `test_dedupe.py` | Alert debounce window boundaries (`freezegun`) |
| `test_normalise.py` | Unit conversion and clamping of impossible values |

Boundary conditions matter more than happy paths here — a threshold that is wrong by one
comparison operator silently changes every result in the project.
