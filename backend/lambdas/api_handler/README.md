# `api_handler`

**Trigger:** API Gateway HTTP API (Cognito JWT authorizer)
**Memory / timeout:** 256 MB / 10 s

Serves the dashboard. Routes and payloads are specified in
[`docs/architecture/API_CONTRACT.md`](../../../docs/architecture/API_CONTRACT.md).

| Method | Route |
|---|---|
| GET | `/v1/devices` |
| POST | `/v1/devices` (admin) |
| GET | `/v1/devices/{deviceId}/vitals` |
| GET | `/v1/devices/{deviceId}/vitals/latest` |
| GET | `/v1/alerts` |
| POST | `/v1/alerts/{alertId}/ack` |
| GET | `/v1/health` (unauthenticated) |

## Security
A valid JWT is **not** sufficient. Every device-scoped route must additionally verify that
the caller's Cognito `sub` matches `Devices.ownerSub` — otherwise any authenticated user can
read every patient's data. This is the single most likely security bug in the project; it
gets a dedicated test.

## Performance
- Cursor pagination via DynamoDB `LastEvaluatedKey`, base64-encoded. Never `Scan`.
- Cap `limit` server-side (default 500) so one request cannot drain the free RCU allowance.

## TODO (B-5)
- [ ] `app.py` with a small router (or use `aws-lambda-powertools`)
- [ ] `api/openapi.yaml`
- [ ] Ownership-check middleware + its test
- [ ] RFC 7807 error responses
