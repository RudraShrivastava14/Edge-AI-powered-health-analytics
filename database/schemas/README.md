# Table Schemas

JSON definitions mirroring the DynamoDB resources in the CloudFormation template. They exist
so the schema is reviewable in one place and so tests can create identical tables under
`moto` without parsing CloudFormation.

| File | Table | Status |
|---|---|---|
| `telemetry.json` | `Telemetry` — vital summaries, TTL 30 d | TODO (B-6a) |
| `alerts.json` | `Alerts` — confirmed anomalies + `status-index` GSI | TODO (B-6a) |
| `devices.json` | `Devices` — registry and per-device thresholds | TODO (B-6a) |

Full design, access patterns, and design rules: [`../README.md`](../README.md).

**If you change a schema here, change the CloudFormation template in the same PR.** Two
sources of truth that disagree is worse than one that is slightly out of date.
