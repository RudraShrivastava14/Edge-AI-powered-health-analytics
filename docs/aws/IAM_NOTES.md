# IAM & Security Notes

Principle: **every identity gets the narrowest set of permissions that lets it do its job,
and nothing more.** No `Action: "*"`, no `Resource: "*"` outside of the few APIs that
genuinely require it (e.g. `logs:CreateLogGroup` at deploy time).

---

## 1. Identities in the System

| Identity | Type | Purpose |
|---|---|---|
| Team member users | IAM user / Identity Center | Development and deployment |
| `GitHubActionsDeployRole` | IAM role (OIDC trust) | CI/CD — no long-lived access keys |
| `IngestFunctionRole` | Lambda execution role | Write telemetry, archive windows, invoke processor |
| `AnomalyProcessorRole` | Lambda execution role | Read windows, write alerts, invoke dispatcher |
| `AlertDispatcherRole` | Lambda execution role | Read/write alerts, publish to SNS |
| `ApiHandlerRole` | Lambda execution role | Read-only on telemetry/alerts, update alert status |
| `IoTRuleInvokeRole` | Service role | Let the IoT Rules Engine invoke the ingest Lambda |
| Device certificates | X.509 + IoT policy | Publish on that device's topic only |

---

## 2. Per-Lambda Permission Matrix

| Function | DynamoDB | S3 | Other |
|---|---|---|---|
| `ingest_handler` | `PutItem`, `BatchWriteItem` on **Telemetry** | `PutObject` on `raw-windows/*` | `lambda:InvokeFunction` on `anomaly_processor` |
| `anomaly_processor` | `PutItem` on **Alerts**; `UpdateItem` on **Telemetry** | `GetObject` on `raw-windows/*`, `GetObject` on `models/*` | `lambda:InvokeFunction` on `alert_dispatcher` |
| `alert_dispatcher` | `Query`, `UpdateItem` on **Alerts** | — | `sns:Publish` on the alerts topic |
| `api_handler` | `Query`, `GetItem` on **Telemetry**, **Alerts**, **Devices**; `UpdateItem` on **Alerts** | — | — |

All four additionally get the managed `AWSLambdaBasicExecutionRole` (CloudWatch Logs) and,
where enabled, X-Ray write permissions.

---

## 3. Device IoT Policy (template)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "iot:Connect",
      "Resource": "arn:aws:iot:${Region}:${Account}:client/${iot:Connection.Thing.ThingName}" },
    { "Effect": "Allow", "Action": "iot:Publish",
      "Resource": [
        "arn:aws:iot:${Region}:${Account}:topic/hh/v1/${iot:Connection.Thing.ThingName}/telemetry",
        "arn:aws:iot:${Region}:${Account}:topic/hh/v1/${iot:Connection.Thing.ThingName}/status"
      ] },
    { "Effect": "Allow", "Action": ["iot:Subscribe"],
      "Resource": "arn:aws:iot:${Region}:${Account}:topicfilter/hh/v1/${iot:Connection.Thing.ThingName}/config" },
    { "Effect": "Allow", "Action": ["iot:Receive"],
      "Resource": "arn:aws:iot:${Region}:${Account}:topic/hh/v1/${iot:Connection.Thing.ThingName}/config" }
  ]
}
```

The `${iot:Connection.Thing.ThingName}` policy variable is what prevents a compromised
device from publishing as another device. Do **not** replace it with a wildcard.

---

## 4. Secrets Handling

- **Nothing secret is committed.** `.gitignore` covers `*.pem`, `*.key`, `certs/`, `.env`,
  `.outputs.json`.
- Runtime configuration (thresholds, model version, SNS topic ARN) → **SSM Parameter Store**
  (standard tier, free); secrets, if any ever appear, → Secrets Manager or an SSM
  `SecureString`.
- CI authenticates via **GitHub OIDC → IAM role assumption**. No `AWS_ACCESS_KEY_ID` secret
  in GitHub.
- `gitleaks` runs in CI on every PR.

**If a credential is ever committed:** rotate/revoke it in AWS first, then clean history.
Deleting the commit is not sufficient — assume it is compromised.

---

## 5. Data Protection

| Control | Setting |
|---|---|
| In transit (device) | TLS 1.2 with mutual X.509 auth |
| In transit (client) | HTTPS only; CloudFront redirects HTTP |
| At rest (S3) | SSE-S3 (AES-256); Block Public Access on, except the SPA bucket which is served only via CloudFront OAC |
| At rest (DynamoDB) | AWS-owned key encryption enabled |
| Logs | No payload bodies at `INFO`; IDs and metrics only |
| Retention | Telemetry TTL 30 days; S3 raw windows expire at 90 days |
| PII | None collected — device IDs are opaque; any mapping to a person lives outside this system |

---

## 6. Pre-Submission Security Checklist

- [ ] Root account has MFA and is unused for day-to-day work
- [ ] No IAM policy in the template contains `"Action": "*"`
- [ ] S3 Block Public Access enabled on every bucket
- [ ] Device certificates are not in git history (`git log --all -- '*.pem'` is empty)
- [ ] API Gateway routes all sit behind the Cognito JWT authorizer (except `/v1/health`)
- [ ] `api_handler` verifies device ownership, not just JWT validity
- [ ] CloudWatch log retention set on every log group
- [ ] Budget alarm active
- [ ] `gitleaks` passing in CI
