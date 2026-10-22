# Database — DynamoDB Design

Owner: **Krish Agarwal (KA)**.

We use **Amazon DynamoDB** for the hot store and **S3** for cold/raw data. Rationale in
[ADR-2](../docs/architecture/ARCHITECTURE.md#6-key-design-decisions-adr-summary): 25 GB of
DynamoDB is *always* free, whereas the RDS allowance expires after 12 months.

---

## Tables

### 1. `Telemetry`

Vital-sign summaries, one item per 10-second window.

| Attribute | Type | Notes |
|---|---|---|
| `pk` | S | `DEV#<deviceId>` — partition key |
| `sk` | S | `TS#<epochMillis>#<seq>` — sort key, gives natural time ordering |
| `ts` | N | epoch ms (duplicated for projections/filters) |
| `hr`, `spo2`, `tempC` | N | window means |
| `hrMin`, `hrMax`, `sdnn` | N | window statistics |
| `activity` | S | `rest` \| `walk` \| `run` \| `unknown` |
| `flag` | S | `normal` \| `suspect` \| `critical` (edge verdict) |
| `reconError` | N | edge reconstruction error |
| `modelVersion` | S | e.g. `ae-int8-1.2.0` |
| `rawS3Key` | S | present only when a window was archived |
| `edgeFp` | BOOL | set by `anomaly_processor` when the cloud rejects the edge's flag |
| `expiresAt` | N | **TTL attribute — 30 days**, keeps us inside the free storage tier |

**Access patterns**
- Latest reading for a device → `Query pk = DEV#id, ScanIndexForward = false, Limit = 1`
- Range query → `Query pk = DEV#id AND sk BETWEEN TS#from AND TS#to`

### 2. `Alerts`

| Attribute | Type | Notes |
|---|---|---|
| `pk` | S | `DEV#<deviceId>` |
| `sk` | S | `ALERT#<epochMillis>#<alertId>` |
| `alertId` | S | ULID |
| `class` | S | `tachycardia` \| `bradycardia` \| `arrhythmia` \| `hypoxia` \| `unknown` |
| `severity` | S | `low` \| `medium` \| `high` |
| `confidence` | N | cloud model confidence 0–1 |
| `status` | S | `open` \| `acknowledged` \| `resolved` |
| `evidenceS3Key` | S | the raw window that triggered it |
| `ackBy`, `ackNote`, `ackTs` | S/S/N | acknowledgement metadata |

**GSI `status-index`:** `gsi1pk = STATUS#<status>`, `gsi1sk = TS#<epochMillis>` — powers the
"all open alerts across the fleet, newest first" view without a table scan.

### 3. `Devices`

| Attribute | Type | Notes |
|---|---|---|
| `pk` | S | `DEV#<deviceId>` |
| `sk` | S | `META` |
| `label` | S | human-readable, e.g. "Ward A – Bed 3" |
| `ownerSub` | S | Cognito subject allowed to view it (authorisation check in `api_handler`) |
| `status` | S | `online` \| `offline` |
| `lastSeen` | N | epoch ms |
| `fwVersion`, `battery` | S/N | from the status topic |
| `thresholds` | M | per-device `τ_low` / `τ_high` overrides |

---

## Design rules

1. **No `Scan` in application code.** Every read is a `Query` on a key or a GSI. A scan on a
   growing telemetry table will silently eat the free RCU allowance.
2. **TTL is mandatory on `Telemetry`.** Without it, storage grows unbounded and eventually
   exits the free tier.
3. **On-demand capacity mode** — no capacity planning, and it scales for the elasticity demo.
4. **Hot partitions:** the partition key is the device ID, so load spreads across devices
   naturally. A single device cannot exceed 3 000 RCU / 1 000 WCU, far above our rate.
5. **Numbers stay numbers.** Store `hr` as `N`, not `S`, so range conditions work.

## Layout

```
database/
├── schemas/     table definitions (JSON) mirroring the CloudFormation resources
├── seed/        seed_devices.json, sample telemetry for local/dev testing
└── README.md
```

## TODO

- [ ] B-6a `schemas/telemetry.json`, `alerts.json`, `devices.json`
- [ ] B-6b Seed script (`seed/load.py`) using boto3 against the dev stack or DynamoDB Local
- [ ] B-6c Access-pattern test suite proving no query needs a scan
- [ ] Document the capacity-consumption measurements for the report
