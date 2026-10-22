# GitHub Actions

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | push / PR to `main`, `dev` | Lint, simulator smoke test, unit + integration tests, CloudFormation validation, frontend build, secret scan, docs link check |
| `deploy.yml` | push to `main` (TODO, I-5) | `sam build` + `sam deploy` to the `prod` stack via **GitHub OIDC role assumption** |

## Rules

- **No AWS access keys in GitHub secrets.** `deploy.yml` assumes an IAM role through OIDC;
  the trust policy is scoped to this repository. See
  [`docs/aws/IAM_NOTES.md`](../../docs/aws/IAM_NOTES.md).
- CI never runs live AWS tests — they cost free-tier quota and need credentials.
- The secret scan is **not** `continue-on-error`. A committed credential fails the build.
