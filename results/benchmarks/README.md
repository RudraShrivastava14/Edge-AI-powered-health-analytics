# Benchmarks

One file per experiment, following the template in [`../README.md`](../README.md).

| File | Experiment | Owner | Status |
|---|---|---|---|
| `model_eval.md` | E1–E3: accuracy, quantisation delta, cascade | MR | ☐ |
| `latency.md` | E4: end-to-end and per-stage latency | KA | ☐ |
| `bandwidth.md` | E5: uplink reduction vs. stream-everything | MR | ☐ |
| `scalability.md` | E6: 1 → 50 → 200 devices | KA | ☐ |
| `cost.md` | E7: actual bill + projection | KA | ☐ |
| `resilience.md` | E8: offline buffering and replay | MR | ☐ |
| `runs/` | Per-training-run directories: config, seed, commit, metrics | MR | ☐ |

## Current placeholder measurement

The edge simulator with the **stub** scorer (not the trained model) reports **86.8 % uplink
reduction** over 400 mixed-profile windows against a compressed stream-everything baseline:

```bash
cd edge && python -m simulator.run --device-id demo-001 --profile mixed \
    --dry-run --windows 400 --interval 0 --seed 7
```

This is a pipeline sanity check, **not** result E5. Re-run it with the trained TFLite model
before quoting any number in the report, and state which scorer produced it.
