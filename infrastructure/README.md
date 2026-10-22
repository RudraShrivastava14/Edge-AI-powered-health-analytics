# Infrastructure — Infrastructure as Code

Owner: **Krish Agarwal (KA)**.

The **entire** cloud tier is defined here. Nothing is created by clicking in the AWS
console — if it is not in the template, it does not exist. This is what makes the project
reproducible (research gap G5).

## Layout

```
infrastructure/
├── cloudformation/
│   ├── template.yaml        main SAM template (all resources)
│   ├── iot.yaml             IoT things, policies, rules
│   ├── data.yaml            DynamoDB tables + S3 buckets
│   └── parameters/          dev.json, prod.json
├── scripts/
│   ├── deploy.sh            sam build + deploy, writes .outputs.json
│   ├── destroy.sh           empties buckets, deletes the stack
│   ├── provision_device.sh  creates an IoT thing + certificate
│   ├── budget.json          $1 monthly budget definition
│   └── budget-notifications.json
└── ci/                      shared CI helper scripts
```

## Resources created

| Category | Resources |
|---|---|
| IoT | Thing type, thing group, IoT policy, topic rule → Lambda, rule error action → CloudWatch |
| Compute | 4 Lambda functions + 1 shared layer, per-function IAM roles, reserved concurrency caps |
| Data | 3 DynamoDB tables (on-demand, TTL, 1 GSI), 2 S3 buckets (raw data, web) |
| API | HTTP API, Cognito user pool + client, JWT authorizer, routes |
| Messaging | SNS topic + email subscription, SQS dead-letter queues |
| Observability | Log groups with 7-day retention, alarms on Lambda `Errors`/`Throttles`, a CloudWatch dashboard |
| Delivery | CloudFront distribution + Origin Access Control for the SPA bucket |

## Usage

```bash
./scripts/deploy.sh dev              # deploy/update
./scripts/deploy.sh prod             # the demo stack
./scripts/provision_device.sh demo-001
./scripts/destroy.sh dev             # tear down — do this after benchmarking
```

Stack outputs land in `.outputs.json` (gitignored); the edge simulator and frontend read
their configuration from it.

## Conventions

- **Environment parameter** (`dev` / `prod`) is in every resource name, so both stacks can
  coexist in one account.
- **Tag everything**: `Project=health-analytics`, `Environment=<env>`, `Owner=<team>`. This
  is what makes Cost Explorer's per-project breakdown work.
- **Set `RetentionInDays: 7`** on log groups in the SAM `Globals` block — not per function,
  so none is missed.
- **Reserved concurrency caps** on every function: a bug in the simulator must not be able
  to exhaust the monthly Lambda quota.
- **No VPC.** Lambdas run outside a VPC deliberately — a NAT Gateway costs ~$32/month and is
  never free.
- **`DeletionPolicy: Delete`** on data resources in `dev`, `Retain` in `prod`.

## Validation before every commit

```bash
sam validate --lint
cfn-lint cloudformation/*.yaml
checkov -d cloudformation/          # security posture (optional but nice for the report)
```

## TODO

- [ ] I-2 Author `template.yaml`
- [ ] I-3 `provision_device.sh`
- [ ] I-4 Per-Lambda least-privilege roles (see [`docs/aws/IAM_NOTES.md`](../docs/aws/IAM_NOTES.md))
- [ ] I-6 CloudWatch dashboard + alarms
- [ ] I-8 CloudFront + OAC for the SPA bucket
- [ ] Deploy from a clean account and record the wall-clock time (reproducibility result)
