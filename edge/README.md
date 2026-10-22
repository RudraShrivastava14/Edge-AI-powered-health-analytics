# Edge Tier

Everything that runs **on the wearable gateway** (Raspberry Pi) or, for development, on a
laptop as a simulator. Owner: **Monis Raza (MR)**.

## Purpose

1. Acquire (or synthesise) vital-sign signals.
2. Condition them: bandpass filter, resample to 125 Hz, reject motion artefacts using the
   accelerometer.
3. Slice into 10-second windows with 50 % overlap.
4. Run the INT8 TFLite autoencoder and compute a reconstruction error.
5. Apply the **uplink policy** — this is the core of the project's bandwidth argument:

   | Reconstruction error | Flag | What is published |
   |---|---|---|
   | `e < τ_low` | `normal` | compact summary only (~200 B) |
   | `τ_low ≤ e < τ_high` | `suspect` | summary + downsampled window |
   | `e ≥ τ_high` | `critical` | summary + full window, QoS 1, priority |

6. Buffer to local SQLite when offline; replay critical windows first on reconnect.
7. Publish over MQTT/TLS to AWS IoT Core using per-device X.509 credentials.

## Layout

```
edge/
├── simulator/        synthetic vital-sign generator + CLI runner (no hardware needed)
├── edge_inference/   TFLite runtime wrapper, uplink policy, store-and-forward buffer
├── config/           device settings; certs/ is gitignored
└── requirements.txt
```

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# offline, prints payloads instead of publishing — costs nothing
python -m simulator.run --device-id demo-001 --profile arrhythmia --dry-run

# live against the deployed stack
python -m simulator.run --device-id demo-001 --profile mixed \
  --endpoint <iot-ats-endpoint> --cert-dir config/certs/demo-001
```

## Simulator profiles

| Profile | Emulates |
|---|---|
| `healthy` | Normal sinus rhythm, HR 60–90, SpO₂ 96–99 |
| `tachycardia` | Sustained HR > 120 at rest |
| `bradycardia` | Sustained HR < 50 |
| `arrhythmia` | Irregular RR intervals, ectopic beats |
| `hypoxia` | Progressive SpO₂ desaturation below 90 % |
| `mixed` | Mostly normal with injected episodes — the realistic demo profile |

## Target metrics

| Metric | Target |
|---|---|
| Inference latency per window | < 50 ms on Pi 4 |
| Model size | < 500 KB |
| Uplink reduction vs. stream-everything | ≥ 90 % |
| Offline buffering capacity | ≥ 6 hours |

## TODO

- [ ] M-6a `simulator/generator.py` — physiologically plausible signal synthesis
- [ ] M-6b `edge_inference/model.py` — TFLite interpreter wrapper
- [ ] M-6c `edge_inference/policy.py` — thresholding + activity-aware escalation
- [ ] M-6d `edge_inference/buffer.py` — SQLite ring buffer with prioritised replay
- [ ] M-6e `edge_inference/publisher.py` — `awsiotsdk` MQTT client, reconnect with backoff
- [ ] M-6f Byte/message counters for the bandwidth benchmark
