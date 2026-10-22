# `anomaly_processor`

**Trigger:** async invoke from `ingest_handler` · **Memory / timeout:** 512 MB / 30 s

The **second stage of the cascade**. The edge model is deliberately over-sensitive; this
function's job is to reject its false positives while never discarding a true event.

## Responsibilities
1. Fetch the raw window from S3.
2. Run the full-precision confirmation model (loaded from S3 into `/tmp` at cold start and
   cached in a module-level global so warm invocations reuse it).
3. Cross-check against rule-based physiological limits — a model and a rule disagreeing is
   itself informative.
4. If confirmed: write an item to `Alerts` (class, severity, confidence, evidence S3 key)
   and async-invoke `alert_dispatcher`.
5. If rejected: mark the telemetry item `edgeFp = true`. These hard negatives are the
   training set for the next model revision.

## Design notes
- Load the model **outside** the handler. A cold start that re-downloads weights blows the
  5 s end-to-end latency target.
- Prefer recall over precision when the two conflict at the margin, and say so in the
  report — a missed cardiac event costs more than a spurious notification.

## TODO (B-3)
- [ ] `app.py`, model loader with `/tmp` caching
- [ ] Rule-based cross-check module
- [ ] Severity mapping table
- [ ] Tests, including the cold-start latency measurement for benchmark E4
