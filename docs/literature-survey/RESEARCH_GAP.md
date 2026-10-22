# Research Gap Analysis

**Cloud-Based Wearable Health Analytics Platform using Edge–Cloud Intelligence**

This document states, precisely, what the reviewed literature does *not* do, and what this
project contributes as a result. It is the bridge between
[`LITERATURE_SURVEY.md`](LITERATURE_SURVEY.md) and the objectives in the root `README.md`.

---

## 1. Identified Gaps

### Gap 1 — Cascaded (two-stage) inference is unvalidated for physiological streams

Early-exit and model-partitioning schemes (Neurosurgeon [6], DDNN [7]) are demonstrated on
image classification, where a "sample" is a discrete, independent input. Physiological data
is a *continuous, non-stationary, subject-specific* stream, where the interesting events are
rare (class imbalance often > 100:1) and context-dependent (a heart rate of 160 bpm is
normal while running, alarming at rest). No reviewed work evaluates an edge-screen →
cloud-confirm cascade on wearable vital signs with an explicit false-negative budget.

> **What we do:** implement the cascade for 10-second physiological windows, use IMU-derived
> activity context to modulate the escalation threshold, and report the operating curve —
> uplink volume vs. recall — rather than a single accuracy number.

### Gap 2 — Bandwidth/energy savings are asserted, not measured

Fog-computing healthcare papers [3] claim reduced transmission but rarely publish a
byte-level comparison against a stream-everything baseline under identical signal
conditions, and almost never relate it to a monetary or quota cost.

> **What we do:** instrument the edge uplink with byte and message counters; report
> percentage reduction versus baseline, and translate it into IoT Core messages consumed per
> device per day — the number that actually determines whether the deployment fits the Free
> Tier.

### Gap 3 — Deep ECG models exist in isolation from deployable systems

State-of-the-art ECG models [9][10] are large (tens of MB, millions of parameters) and are
evaluated offline on curated datasets. The literature does not carry them through
quantisation, latency measurement on real edge hardware, and integration into a production
data path.

> **What we do:** train, then INT8-quantise to a < 500 KB TFLite artefact, measure per-window
> latency on a Raspberry Pi 4, and report the accuracy delta introduced by quantisation as a
> first-class result rather than a footnote.

### Gap 4 — Health-IoT backends are rarely serverless, and their cost is almost never reported

Reviewed systems use VMs, containers, or on-premise gateways. The serverless literature [14]
[15] analyses economics generically but not for a continuous-telemetry health workload. We
found no health-IoT paper that publishes an actual monthly bill or a per-device cost model.

> **What we do:** build the entire cloud tier from FaaS + managed services, publish a
> component-by-component Free Tier budget ([`docs/aws/FREE_TIER_BUDGET.md`](../aws/FREE_TIER_BUDGET.md)),
> demonstrate a $0 demo-scale bill, and extrapolate cost per 1 000 devices beyond Free Tier.

### Gap 5 — Reproducibility

Architectures in this space are published as block diagrams. Almost none ship
infrastructure-as-code, so results cannot be re-created by a reader.

> **What we do:** the whole stack is one CloudFormation/SAM template plus a deploy script;
> the simulator removes the hardware barrier entirely, so any reader with an AWS account can
> reproduce the pipeline end-to-end.

### Gap 6 — Resilience of the edge link is under-treated

Wearable gateways operate on intermittent connectivity, yet evaluations assume a stable
uplink. Data loss during disconnection is seldom quantified.

> **What we do:** a store-and-forward buffer with bounded storage and prioritised replay
> (critical windows first), plus a chaos test that severs the network for a defined interval
> and measures data loss and replay latency.

---

## 2. Gap-to-Contribution Matrix

| Gap | Contribution | Where implemented | How evaluated |
|---|---|---|---|
| G1 Cascade unvalidated on vitals | Anomaly-triggered edge→cloud escalation with activity-aware thresholds | `edge/edge_inference/`, `backend/lambdas/anomaly_processor/` | Recall/precision vs. uplink-volume operating curve |
| G2 Savings unmeasured | Byte/message instrumentation vs. stream-everything baseline | `edge/simulator/` counters | `results/benchmarks/bandwidth.md` |
| G3 Models not deployable | INT8 TFLite pipeline + on-device latency harness | `ai-models/training/`, `ai-models/models/` | Accuracy delta + ms/window on Pi 4 |
| G4 Cost unreported | Fully serverless tier + published budget | `infrastructure/` | AWS Cost Explorer + projection model |
| G5 Not reproducible | One-command IaC + hardware-free simulator | `infrastructure/scripts/deploy.sh` | Clean-account deploy from scratch, timed |
| G6 Link resilience | Prioritised store-and-forward buffer | `edge/edge_inference/buffer.py` | Chaos test: 30 min offline, measure loss |

---

## 3. Research Questions

- **RQ1.** For 10 s wearable vital-sign windows, what edge-threshold setting minimises uplink
  volume subject to a false-negative rate below 5 % on MIT-BIH-derived anomalies?
- **RQ2.** How much accuracy is lost by INT8 quantisation of the edge autoencoder, and is the
  loss recovered by the cloud confirmation stage?
- **RQ3.** What is the p95 end-to-end latency from an anomalous sample to a delivered
  notification in a purely serverless AWS pipeline, and what dominates it (cold start,
  IoT Rule dispatch, or SNS delivery)?
- **RQ4.** At what device count does the architecture exit the AWS Free Tier, and what is the
  marginal cost per device per month beyond that point?
- **RQ5.** Does incorporating accelerometer-derived activity context measurably reduce
  motion-artefact false positives compared with an ECG/HR-only detector?

---

## 4. Scope and Limitations (stated up front)

- **Not a medical device.** No clinical validation, no regulatory claim (this is an academic
  prototype).
- **Datasets are clinical, not wearable-grade.** MIT-BIH was recorded with clinical
  electrodes; wrist-worn PPG is noisier. We mitigate by injecting realistic noise and motion
  artefacts during training, and we state this as a threat to external validity.
- **Federated learning is future work,** not implemented — it needs a client population we do
  not have.
- **Single AWS region,** no multi-region failover (cross-region traffic is billable).
- **Free Tier constrains scale.** Sustained load tests are short-duration and bounded so the
  account stays within quota.

---

## 5. Novelty Statement (one paragraph, for the report)

> Existing wearable-health platforms either stream all raw physiological data to the cloud —
> which is expensive, energy-hungry, and slow to alert — or run detection entirely on the
> edge, which caps model capacity. Cascaded inference has been shown to resolve this tension
> for computer vision, but has not been validated on continuous, highly imbalanced,
> context-dependent physiological streams. This project implements and empirically evaluates
> such a cascade end-to-end: a sub-500 KB quantised autoencoder screens 10-second windows on
> the device and escalates only suspicious ones to a higher-capacity confirmation model
> running in a fully serverless AWS backend. The contribution is threefold: (i) an
> activity-aware escalation policy with a measured recall-versus-bandwidth operating curve,
> (ii) an end-to-end latency and accuracy evaluation of the deployed cascade rather than the
> model alone, and (iii) a fully reproducible, infrastructure-as-code deployment with a
> published cost model demonstrating that the architecture operates at zero cost within the
> AWS Free Tier at demo scale.
