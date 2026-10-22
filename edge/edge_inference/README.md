# Edge Inference

| File | Status | Purpose |
|---|---|---|
| `policy.py` | Implemented (scorer stubbed) | Thresholds, flag classification, payload construction, window encoding, bandwidth counters |
| `model.py` | TODO (M-6b) | TFLite interpreter wrapper — loads `models/autoencoder_int8.tflite`, returns reconstruction error |
| `buffer.py` | TODO (M-6d) | SQLite ring buffer, prioritised replay (critical windows first) |
| `publisher.py` | TODO (M-6e) | Long-lived MQTT connection, reconnect with exponential backoff, config-topic subscription |

## Current state of `score_window`

`policy.score_window` is a **placeholder heuristic** based on heart-rate deviation, RR
coefficient of variation, and SpO2 — not the trained model. It exists so the pipeline is
end-to-end runnable today. Replacing it with the TFLite interpreter is task M-6b, and the
function signature will not change.

Measured with the placeholder over 400 mixed-profile windows: **86.8 % uplink reduction**
versus a compressed stream-everything baseline. The ≥90 % objective assumes the trained
model flags fewer windows than the heuristic does — verify this after M-5 and report the
real number in `results/benchmarks/bandwidth.md`. Do not quote the target as if it were a
result.

## Threshold tuning

`Thresholds` are activity-scaled: motion inflates reconstruction error, so tolerance rises
while the wearer moves. Values are chosen on the validation set at a fixed false-negative
budget and can be overridden per device at runtime via the `hh/v1/{deviceId}/config` topic —
so the operating point is tunable without reflashing devices.
