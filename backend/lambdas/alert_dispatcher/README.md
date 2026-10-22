# `alert_dispatcher`

**Trigger:** async invoke from `anomaly_processor` · **Memory / timeout:** 128 MB / 10 s

## Responsibilities
1. Deduplicate and debounce: at most **one notification per device per alert class per
   5 minutes**. Without this, a sustained arrhythmia produces a notification every 10
   seconds and the caregiver stops reading them.
2. Format a human-readable message (device label, class, severity, time, dashboard link).
3. Publish to the SNS topic; SNS fans out to email and, optionally, SMS.
4. Record the notification on the alert item (`notifiedAt`, `channel`).

## Debounce state
Held in the `Alerts` table keyed on `DEV#<id>` + `DEDUPE#<class>` with a TTL equal to the
debounce window — no extra table, no extra cost.

## Free Tier note
SNS email is capped at **1 000 notifications/month**. The debounce is what keeps a demo
run from consuming the month's allowance in an afternoon.

## TODO (B-4)
- [ ] `app.py` with the debounce check
- [ ] Message templates per severity
- [ ] Tests using `freezegun` for the debounce window boundaries
