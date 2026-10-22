# CI Helpers

Shared scripts called by GitHub Actions, kept here rather than inlined in the workflow YAML
so they can be run locally and reviewed as code.

| Script | Purpose | Status |
|---|---|---|
| `lint.sh` | `ruff` + `cfn-lint` + `sam validate` | TODO (I-5) |
| `test.sh` | `pytest tests/unit tests/integration` with coverage | TODO (I-5) |
| `secrets_scan.sh` | `gitleaks detect` — fails the build on any committed credential | TODO (I-5) |

## AWS authentication in CI

**GitHub OIDC → IAM role assumption. No long-lived access keys in GitHub secrets, ever.**
The deploy role trusts the repository's OIDC subject and is scoped to the CloudFormation
stack it manages. Setup is documented in [`docs/aws/IAM_NOTES.md`](../../docs/aws/IAM_NOTES.md).
