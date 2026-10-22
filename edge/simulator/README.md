# Simulator

Hardware-free synthetic wearable. Lets the whole pipeline be built, demoed and load-tested
without a Raspberry Pi or a real device.

| File | Purpose |
|---|---|
| `generator.py` | Synthesises 10 s windows: PQRST-shaped ECG at a profile-specific rate, RR irregularity, SpO2, temperature, accelerometer, activity context. Implemented. |
| `run.py` | CLI: generates → scores → applies the uplink policy → prints (`--dry-run`) or publishes over MQTT. Reports bandwidth counters on exit. Implemented. |

```bash
python -m simulator.run --device-id demo-001 --profile mixed --dry-run --windows 400 --interval 0 --seed 7
```

`--interval 0` compresses a 400-window (≈67 min) run into a second — use it for benchmarks
and demos; use the real `--interval 10` when publishing to AWS so the message rate stays
inside the free-tier quota.

## TODO

- [ ] Multi-device mode (`--devices 50`) for scalability benchmark E6
- [ ] Replay mode: stream real MIT-BIH records instead of synthetic signal, so the demo can
      show the model reacting to genuine arrhythmias
- [ ] Network-chaos flag (`--drop-after`, `--reconnect-after`) for resilience benchmark E8
