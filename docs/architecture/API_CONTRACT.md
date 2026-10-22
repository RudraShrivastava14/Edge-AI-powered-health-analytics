# API & Message Contracts

Two contracts are defined here: the **device→cloud MQTT payload** and the **client→cloud
REST API**. Both are versioned; breaking changes bump the version in the topic/path.

---

## 1. MQTT Topics

| Topic | Direction | Purpose | QoS |
|---|---|---|---|
| `hh/v1/{deviceId}/telemetry` | device → cloud | Vital-sign summaries and event windows | 0 (normal), 1 (critical) |
| `hh/v1/{deviceId}/status` | device → cloud | Connect/disconnect, battery, firmware version | 1 |
| `hh/v1/{deviceId}/config` | cloud → device | Threshold updates, sampling rate, model version | 1 |

IoT policy restricts each device to its own `{deviceId}` prefix.

---

## 2. Telemetry Payload (v1)

```jsonc
{
  "schema": "hh.telemetry.v1",
  "deviceId": "demo-001",            // opaque UUID or lab ID — never a patient name
  "ts": 1753900000123,               // epoch milliseconds, device clock (NTP-synced)
  "seq": 41827,                      // monotonic counter, for gap detection
  "window": {
    "durationMs": 10000,
    "sampleRateHz": 125
  },
  "vitals": {                        // aggregate summary of the window
    "hr":       { "mean": 78.2, "min": 71, "max": 86, "sdnn": 42.7 },
    "spo2":     { "mean": 97.8, "min": 96 },
    "tempC":    { "mean": 36.6 },
    "activity": "rest"               // rest | walk | run | unknown  (IMU-derived)
  },
  "edge": {                          // edge inference result
    "modelVersion": "ae-int8-1.2.0",
    "reconError": 0.0142,
    "flag": "normal",                // normal | suspect | critical
    "inferenceMs": 31
  },
  "raw": {                           // present only when flag != "normal"
    "encoding": "b64+gzip+float16",
    "channels": ["ecg"],
    "s3Hint": null,                  // set by ingest_handler after archival
    "data": "H4sIAAAAA…"
  },
  "meta": {
    "battery": 0.82,
    "fwVersion": "0.3.1",
    "bufferedReplay": false          // true if this is a replayed offline message
  }
}
```

**Rules**

- No PII. `deviceId` is opaque; the mapping to a person, if any, lives outside this system.
- Payload must stay under **128 KB** (IoT Core limit); summaries target < 300 B.
- Unknown fields are ignored by the consumer (forward compatibility); missing required
  fields cause the message to be quarantined, not dropped silently.
- Machine-readable JSON Schema: `backend/common/schemas/telemetry.v1.json`.

---

## 3. REST API

Base URL: the `ApiEndpoint` stack output. All routes require
`Authorization: Bearer <Cognito JWT>`. All timestamps are epoch milliseconds, UTC.

### `GET /v1/devices`
List devices the caller is authorised to view.
```json
{ "devices": [ { "deviceId": "demo-001", "label": "Ward A – Bed 3",
                 "status": "online", "lastSeen": 1753900000123,
                 "fwVersion": "0.3.1", "battery": 0.82 } ] }
```

### `GET /v1/devices/{deviceId}/vitals?from={ts}&to={ts}&limit=500&cursor=<token>`
Time-ordered vital summaries. Cursor-paginated (DynamoDB `LastEvaluatedKey`, base64).
```json
{ "deviceId": "demo-001",
  "items": [ { "ts": 1753900000123, "hr": 78.2, "spo2": 97.8,
               "tempC": 36.6, "activity": "rest", "flag": "normal" } ],
  "nextCursor": null }
```

### `GET /v1/devices/{deviceId}/vitals/latest`
Single most recent summary — used by the live view's poll loop.

### `GET /v1/alerts?status=open&severity=high&limit=50`
```json
{ "items": [ { "alertId": "01J…", "deviceId": "demo-001", "ts": 1753900012000,
               "class": "tachycardia", "severity": "high", "confidence": 0.94,
               "status": "open", "evidenceS3Key": "raw-windows/2026/07/31/demo-001/…npz" } ],
  "nextCursor": null }
```

### `POST /v1/alerts/{alertId}/ack`
Body: `{ "note": "reviewed, patient was exercising" }` → `200 { "status": "acknowledged" }`

### `POST /v1/devices` *(admin)*
Register a device: `{ "deviceId": "demo-002", "label": "Ward A – Bed 4" }`

### `GET /v1/health`
Unauthenticated liveness probe: `{ "status": "ok", "version": "0.1.0" }`

---

## 4. Errors

RFC 7807-style problem detail:

```json
{ "type": "https://…/errors/validation", "title": "Invalid query range",
  "status": 400, "detail": "'from' must be before 'to'", "requestId": "abc-123" }
```

| Status | When |
|---|---|
| 400 | Malformed parameters |
| 401 | Missing/invalid JWT |
| 403 | Valid JWT but not authorised for that device |
| 404 | Unknown device or alert |
| 429 | Throttled by API Gateway |
| 500 | Unhandled — always carries a `requestId` for log correlation |

---

## 5. Versioning Policy

- Additive changes (new optional fields) do **not** bump the version.
- Removals, renames, or semantic changes bump `v1` → `v2` in both the topic and the path.
- The cloud accepts `v1` for at least one release after `v2` ships, so edge devices can be
  updated gradually.
