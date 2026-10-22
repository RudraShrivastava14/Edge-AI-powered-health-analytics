# Frontend — Health Analytics Dashboard

React 18 + Vite single-page app, hosted on **S3 + CloudFront**.
Owner: **Rudra Srivastav (RS)**.

## Views

| Route | View | Contents |
|---|---|---|
| `/login` | Login | Cognito hosted-UI or embedded Amplify Auth flow |
| `/` | Overview | Device fleet grid, online/offline, open-alert count |
| `/devices/:id` | Live Vitals | HR, SpO₂, temperature streaming charts; current edge flag; latency badge |
| `/devices/:id/trends` | Trends | Time-range picker (1 h / 24 h / 7 d / 30 d), aggregate charts, HRV summary |
| `/alerts` | Alert Timeline | Filterable by severity/status, with the raw ECG window that triggered each alert; acknowledge action |
| `/devices` | Device Management | Register, label, deactivate a device |

## Stack

- **React 18 + Vite** — fast dev server, tiny production bundle
- **Recharts** — time-series charts
- **AWS Amplify Auth** (`aws-amplify/auth`) — Cognito, JWT attached to every API call
- **TanStack Query** — polling, caching, retry/backoff against the REST API
- **CSS custom properties** — light/dark theme

## Configuration

Copy `.env.example` → `.env` and fill in the CloudFormation stack outputs:

```
VITE_API_ENDPOINT=https://xxxx.execute-api.ap-south-1.amazonaws.com
VITE_USER_POOL_ID=ap-south-1_XXXXXXX
VITE_USER_POOL_CLIENT_ID=XXXXXXXXXXXXXXXXXXXX
VITE_AWS_REGION=ap-south-1
VITE_POLL_INTERVAL_MS=5000
```

`.env` is gitignored. These values are not secrets, but they are environment-specific.

## Commands

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # → dist/
npm run preview
npm run test       # Vitest
```

## Deploy

```bash
npm run build
aws s3 sync dist/ s3://<WebBucket>/ --delete
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths '/*'
```

## Design notes

- **Live view uses polling, not WebSockets.** API Gateway WebSocket connections are billed
  per connection-minute; a 5 s poll against an HTTP API stays inside the free request quota
  and is more than fast enough for a 10 s telemetry cadence. Document this trade-off in the
  report.
- **Alerts must be visually unmissable** — severity colour plus an icon and text label, never
  colour alone (accessibility).
- **Show the data's age.** A stale chart that looks live is worse than an explicit "last
  update 42 s ago".
- Charts should render sensibly with sparse or gapped data — offline replay creates gaps.

## TODO

- [ ] F-1 Vite scaffold, routing, layout shell, theme
- [ ] F-2 Cognito auth flow + protected routes + token refresh
- [ ] F-3 Live vitals with polling and connection-status indicator
- [ ] F-4 Trends with range picker and aggregation
- [ ] F-5 Alert timeline + ECG evidence viewer + acknowledge
- [ ] F-6 Device management
- [ ] Screenshots for the report → `results/figures/`
