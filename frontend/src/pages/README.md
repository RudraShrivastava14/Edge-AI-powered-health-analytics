# Pages

| Page | Route | Contents |
|---|---|---|
| `Login` | `/login` | Cognito sign-in |
| `Overview` | `/` | Fleet grid, online/offline counts, open alerts |
| `LiveVitals` | `/devices/:id` | Polled live vitals, current edge flag, latency badge |
| `Trends` | `/devices/:id/trends` | Historical charts with a time-range picker |
| `Alerts` | `/alerts` | Filterable timeline, ECG evidence, acknowledge action |
| `Devices` | `/devices` | Register, label, deactivate |

Pages own data fetching (TanStack Query) and compose components. Keep business logic out of
JSX — put it in `services/` or a hook.
