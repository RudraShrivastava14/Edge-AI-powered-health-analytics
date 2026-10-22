# Presentation & Report

Owner: **Rudra Srivastav (RS)**, with all members presenting their own area.

## Contents (to be added)

```
presentation/
├── slides.pptx / slides.pdf     final deck
├── DEMO_SCRIPT.md               step-by-step live-demo runbook (below)
├── poster.pdf                   if a poster session is required
├── report/                      final written report (LaTeX or DOCX) + figures
└── video/                       backup demo recording — link only, not the file
```

## Suggested Slide Flow (15–18 slides)

| # | Slide | Owner |
|---|---|---|
| 1 | Title, team, course | RS |
| 2 | Motivation — wearables generate data nobody uses in time | RS |
| 3 | Problem statement (bandwidth, latency, cost) | RS |
| 4 | Literature survey — what exists | RS |
| 5 | Research gap — what does not exist | RS |
| 6 | Objectives | RS |
| 7 | **Architecture diagram** (the anchor slide) | KA |
| 8 | Why serverless — Free Tier economics, the ADR table | KA |
| 9 | Edge tier — signal → window → TFLite → uplink policy | MR |
| 10 | Cloud tier — IoT Core → Lambda → DynamoDB → SNS | KA |
| 11 | The cascade — the core idea, with the escalation diagram | MR |
| 12 | Model results — PR curve, confusion matrix, quantisation delta | MR |
| 13 | System results — latency p50/p95, bandwidth saving, scalability | KA |
| 14 | Cost analysis — the $0 bill and the beyond-Free-Tier projection | KA |
| 15 | **Live demo** | all |
| 16 | Limitations and threats to validity (be honest — examiners reward this) | RS |
| 17 | Future work — federated learning, on-device retraining, multi-region | MR |
| 18 | Conclusion + references | RS |

## Live Demo Script (rehearse this at least twice)

1. **Show the deployed stack** — CloudFormation console, resource list. "None of this was
   clicked; it is one template."
2. **Start the simulator** on the `healthy` profile. Show the dashboard live view updating.
3. **Show the message rate** — one summary per 10 s, ~200 bytes. Contrast with the
   stream-everything number on the bandwidth slide.
4. **Switch to the `arrhythmia` profile.** Narrate: edge reconstruction error climbs → flag
   escalates to `critical` → full window uploaded.
5. **The alert arrives** — SNS email on screen, alert appears in the dashboard timeline with
   its ECG evidence. Point at the elapsed time (target < 5 s).
6. **Acknowledge the alert** in the UI; show the DynamoDB item updating.
7. **Elasticity** — launch 50 simulated devices; show the CloudWatch
   `ConcurrentExecutions` graph rising with zero configuration change.
8. **Cost Explorer: $0.00.**
9. **Offline resilience** (if time) — kill the network, keep generating, restore it, show the
   buffered replay arriving.

**Have a fallback.** Record the full demo in advance and keep the video on the presenting
laptop. Conference/college Wi-Fi fails; a recorded demo shown calmly beats a live demo that
hangs.

## Anticipated Questions

| Question | Short answer |
|---|---|
| "Why not just do everything in the cloud?" | Bandwidth, battery, alert latency, and the IoT message quota — with the measured numbers on the bandwidth slide. |
| "Why not everything on the edge?" | A Pi cannot host a high-capacity model; the cloud stage is what gives us precision. |
| "Is it secure?" | Per-device X.509 with topic-scoped policies, Cognito JWT on the API, TLS everywhere, least-privilege IAM. See `docs/aws/IAM_NOTES.md`. |
| "What happens if the network drops?" | Store-and-forward buffer with prioritised replay — demonstrated in E8. |
| "Is this a medical device?" | No. Academic prototype, no clinical validation — stated in the README and on the limitations slide. |
| "What does it cost at scale?" | The projection table in `results/benchmarks/cost.md`. |
| "What is actually novel?" | Cascaded edge–cloud inference validated on physiological streams, with a deployed, reproducible, cost-measured system — not just a model. |

## Checklist

- [ ] Slides finished and rehearsed (target time: check the course requirement)
- [ ] Demo rehearsed twice; backup video recorded
- [ ] All figures exported from `results/figures/` at presentation resolution
- [ ] Report proofread; every claim traceable to `results/`
- [ ] Repository cleaned: no secrets, no stale TODOs in the README, all names filled in
