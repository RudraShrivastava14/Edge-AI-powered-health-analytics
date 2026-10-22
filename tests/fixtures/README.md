# Test Fixtures

Sample payloads shared by `pytest` and `sam local invoke`, so both exercise identical inputs.

| Fixture | Purpose | Status |
|---|---|---|
| `telemetry_normal.json` | Valid summary-only payload, `flag: normal` | TODO |
| `telemetry_critical.json` | Valid payload with an attached raw window | TODO |
| `telemetry_malformed.json` | Missing a required field — must be quarantined, not raised on | TODO |
| `telemetry_out_of_range.json` | HR of 400 bpm — must fail schema validation | TODO |
| `iot_event.json` | The IoT Rule event envelope wrapping a payload | TODO |
| `apigw_event.json` | API Gateway HTTP API event with a Cognito JWT claim | TODO |

Generate the first two straight from the simulator so they stay in sync with what devices
actually send:

```bash
cd edge && python -m simulator.run --device-id demo-001 --profile mixed \
    --dry-run --windows 5 --interval 0 --seed 7 --verbose
```
