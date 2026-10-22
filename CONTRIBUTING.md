# Contributing

Team conventions. Read this before your first commit.

## Branching

```
main            protected, always deployable, deploys to the prod stack
 └── dev        integration branch
      └── feature/<initials>-<short-description>
```

Never commit directly to `main`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/):

```
feat(edge): add store-and-forward buffer with prioritised replay
fix(ingest): quarantine malformed payloads instead of raising
docs(survey): add three 2024 papers on cascaded inference
infra(iot): scope device policy to the connecting thing name
test(api): cover the cross-device authorisation check
```

## Pull requests

- State the **task ID** from [`docs/WORK_DISTRIBUTION.md`](docs/WORK_DISTRIBUTION.md) that
  the PR closes.
- One approval required, from a member who did not author it.
- CI must be green.
- If the PR changes the API or a schema, it updates
  [`docs/architecture/API_CONTRACT.md`](docs/architecture/API_CONTRACT.md) **in the same PR**.

## Hard rules

1. **Never commit secrets.** No `.pem`, `.key`, `.env`, certificates, account IDs, or ARNs.
   If one lands in a commit, revoke it in AWS first — deleting the commit is not enough.
2. **Never commit dataset files or large model weights.** They go in S3 or stay local.
3. **Never create AWS resources by hand.** If it is not in the CloudFormation template, it
   does not exist and the next person cannot reproduce it.
4. **Tear down after benchmarking.** `infrastructure/scripts/destroy.sh dev`.
5. **Clear notebook outputs before committing.**
6. **Numbers in the report must be traceable** to a file in `results/`.

## Code style

- Python: `ruff` defaults, 100-column lines, type hints on public functions, docstrings that
  say *why* rather than restating the signature.
- JavaScript: Prettier defaults; components in PascalCase, hooks in camelCase.
- Comments explain intent and trade-offs, not mechanics.

## Definition of done

- [ ] Code works and is tested
- [ ] Documentation updated (folder README and any affected contract)
- [ ] No secrets, no large binaries
- [ ] CI green
- [ ] Task ticked in `docs/WORK_DISTRIBUTION.md`
