# Services

| Module | Purpose |
|---|---|
| `api.js` | Typed wrapper over the REST API: attaches the Cognito JWT, retries with backoff, parses RFC 7807 errors, decodes pagination cursors |
| `auth.js` | Cognito sign-in/out, token refresh, current-user helpers (AWS Amplify Auth) |
| `decode.js` | Decode `b64+gzip+float16` raw ECG windows for the evidence chart |
| `types.js` | Shared shapes mirroring `docs/architecture/API_CONTRACT.md` |

**Rule:** if the API contract changes, this folder changes first, and the contract document
changes with it in the same PR.
