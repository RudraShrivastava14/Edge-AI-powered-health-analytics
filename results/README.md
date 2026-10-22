# Results & Evaluation

All measured outcomes live here. Owner: **Rudra Srivastav (RS)**, with data supplied by
whoever ran the experiment.

**Rule: every number in the final report must be traceable to a file in this folder**, and
every file must record how it was produced (command, date, commit hash, environment).

## Layout

```
results/
├── benchmarks/
│   ├── model_eval.md      precision/recall/F1/ROC-AUC, confusion matrices, quantisation delta
│   ├── latency.md         end-to-end and per-stage latency, cold vs. warm
│   ├── bandwidth.md       uplink bytes/messages vs. stream-everything baseline
│   ├── scalability.md     1 → 50 → 200 device load test, Lambda concurrency
│   └── cost.md            actual AWS bill + projection beyond Free Tier
└── figures/               plots and screenshots referenced by the report
```

## Planned Experiments

| ID | Experiment | Answers | Method |
|---|---|---|---|
| E1 | Model accuracy | RQ1 | Subject-disjoint test set; report PR-AUC and the confusion matrix at the chosen τ |
| E2 | Quantisation impact | RQ2 | FP32 vs. INT8 on the identical test set; report Δ per metric and on-device latency |
| E3 | Cascade effectiveness | RQ1, RQ2 | Two-stage confusion matrix vs. edge-only and cloud-only; recall-vs-uplink operating curve |
| E4 | End-to-end latency | RQ3 | 100 injected anomalies; timestamp at sample, IoT ingress, Lambda entry, SNS publish; report p50/p95/p99, cold vs. warm |
| E5 | Bandwidth saving | RQ4 | Byte counters over a 1-hour `mixed`-profile run vs. streaming all raw samples |
| E6 | Scalability | — | 1 → 50 → 200 simulated devices; CloudWatch `ConcurrentExecutions`, `Duration`, `Throttles`, DynamoDB consumed capacity |
| E7 | Cost | RQ4 | Cost Explorer screenshot at demo scale + calculator projection at 100 / 1 000 devices |
| E8 | Offline resilience | — | Sever the network for 30 min mid-run; measure data loss and replay latency |
| E9 | Activity context ablation | RQ5 | Detector with vs. without IMU activity features; compare false-positive rate |

## Results Template

Each benchmark file follows this structure:

```markdown
## Experiment E<n>: <name>
**Date:** | **Commit:** | **Run by:**
**Setup:** hardware, AWS region, stack name, model version, dataset split
**Command:** the exact command used
**Raw output:** path to the CSV/JSON produced
**Results:** table
**Figure:** ../figures/<file>.png
**Observations:** what the numbers mean
**Threats to validity:** what could make this misleading
```

## Reporting Standards

- Report **p50 and p95**, not just the mean — latency distributions here are long-tailed
  because of Lambda cold starts, and hiding that would be dishonest.
- With ~1 % anomaly prevalence, **do not report accuracy**. Use PR-AUC, precision, recall.
- Every plot: labelled axes with units, a caption, and a stated sample size.
- Report **negative results too.** If quantisation costs more accuracy than expected, or the
  cascade underperforms cloud-only on recall, that is a finding — say it.
- Include the raw output files, not just the summary tables.

## Status

| Experiment | Status | Owner |
|---|---|---|
| E1–E3 | ☐ Not started | MR |
| E4, E6 | ☐ Not started | KA |
| E5, E8 | ☐ Not started | MR |
| E7 | ☐ Not started | KA |
| E9 | ☐ Not started | MR |
