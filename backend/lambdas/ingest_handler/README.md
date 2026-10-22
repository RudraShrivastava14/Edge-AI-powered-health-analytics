# `ingest_handler`

**Trigger:** AWS IoT Rule `SELECT * FROM 'hh/v1/+/telemetry'`
**Memory / timeout:** 256 MB / 10 s · **Reserved concurrency:** 10

## Responsibilities
1. Validate the payload against `common/schemas/telemetry.v1.json`.
2. Normalise units (°F → °C, clamp physiologically impossible values).
3. Write the summary item to the `Telemetry` table with a 30-day TTL.
4. If a raw window is attached, decode and archive it to
   `s3://<raw-bucket>/raw-windows/YYYY/MM/DD/<deviceId>/<ts>.npz`.
5. Update `Devices.lastSeen` / `status`.
6. If `edge.flag` is `suspect` or `critical`, async-invoke `anomaly_processor` with the
   S3 key rather than the payload — keeps the invoke payload small.

## Must not
- Raise on a malformed payload. Write it to `quarantine/`, emit the `MalformedPayload`
  metric, return success. IoT Core retries otherwise, forever.
- Log payload bodies — it burns the CloudWatch free-tier allowance.

## TODO (B-2)
- [ ] `app.py` with `lambda_handler(event, context)`
- [ ] Schema validation + quarantine path
- [ ] Idempotent write keyed on `(deviceId, ts, seq)`
- [ ] Unit tests + moto integration tests
