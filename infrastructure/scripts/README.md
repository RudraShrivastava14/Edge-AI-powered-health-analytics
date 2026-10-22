# Deployment Scripts

| Script | Purpose | Status |
|---|---|---|
| `deploy.sh <env>` | `sam build` + `sam deploy`, then write stack outputs to `../.outputs.json` | TODO (I-2) |
| `destroy.sh <env>` | Empty the S3 buckets, delete the stack, verify nothing is orphaned | TODO (I-2) |
| `provision_device.sh <deviceId>` | Create IoT thing + X.509 cert + policy attachment; write to `edge/config/certs/<deviceId>/` | TODO (I-3) |
| `budget.json` | $1 monthly budget definition | TODO (I-1) |
| `budget-notifications.json` | Email notification at 50 % and 100 % | TODO (I-1) |
| `upload_model.sh <version>` | Push the cloud model to `s3://<raw-bucket>/models/<version>/` | TODO (M-7) |
| `deploy_frontend.sh <env>` | `npm run build`, `s3 sync`, CloudFront invalidation | TODO (I-8) |

## Conventions

- `set -euo pipefail` at the top of every script — a half-failed deploy is worse than a
  failed one.
- Take the environment as `$1`, default to `dev`, and **refuse to touch `prod` without an
  explicit confirmation prompt**.
- Idempotent: running twice must be safe.
- Print the resulting resource names, so the next step is copy-pasteable.

## Order of operations for a fresh account

1. `budget.json` (guardrail first — before anything can cost money)
2. `deploy.sh dev`
3. `provision_device.sh demo-001`
4. `upload_model.sh <version>`
5. `deploy_frontend.sh dev`
