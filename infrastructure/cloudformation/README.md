# CloudFormation / SAM Templates

| File | Contents | Status |
|---|---|---|
| `template.yaml` | Main SAM template: Lambdas, layer, API Gateway, Cognito, SNS, DLQs, outputs | TODO (I-2) |
| `iot.yaml` | IoT thing type/group, policy, topic rule + error action | TODO (I-3) |
| `data.yaml` | DynamoDB tables + GSI, S3 buckets, lifecycle rules, CloudFront + OAC | TODO (I-2) |
| `parameters/dev.json`, `parameters/prod.json` | Per-environment parameter values | TODO (I-2) |

## Required parameters

| Parameter | Example | Notes |
|---|---|---|
| `Environment` | `dev` \| `prod` | Suffixed onto every resource name |
| `AlertEmail` | `team@example.com` | SNS subscription — must be confirmed by email |
| `LogRetentionDays` | `7` | Keep low; CloudWatch ingestion is the tightest free-tier limit |
| `MaxConcurrency` | `10` | Reserved concurrency per Lambda — the runaway-simulator guard |

## Required outputs

`IoTEndpoint`, `ApiEndpoint`, `UserPoolId`, `UserPoolClientId`, `TelemetryTableName`,
`AlertsTableName`, `DevicesTableName`, `RawDataBucket`, `WebBucket`, `DistributionId`.

`deploy.sh` writes these to `.outputs.json`, which the simulator and frontend read.

## Before every commit

```bash
sam validate --lint
cfn-lint *.yaml
```

## Free Tier rules encoded in the template
- `RetentionInDays: 7` in `Globals`, so no log group is missed
- `BillingMode: PAY_PER_REQUEST` on every table
- `TimeToLiveSpecification` enabled on `Telemetry`
- S3 lifecycle: `raw-windows/` → Standard-IA at 30 d, expire at 90 d
- Reserved concurrency on every function
- **No VPC** — a NAT Gateway costs ~$32/month and is never free
