# Frontend Source

```
src/
├── components/   reusable UI: VitalCard, ECGChart, AlertBadge, DeviceStatus, TimeRangePicker
├── pages/        route-level views: Overview, LiveVitals, Trends, Alerts, Devices, Login
├── services/     api.js (fetch wrapper + JWT), auth.js (Cognito), types.js
└── main.jsx      app entry, router, providers  (TODO F-1)
```

## Conventions

- **All API access goes through `services/api.js`.** No `fetch` in a component — the token
  refresh and error handling live in one place.
- Components are presentational; data fetching happens in the page via TanStack Query.
- Every view must render three states: loading, empty, and error. A blank screen when the
  API is down is a bug, not an edge case.
- **Show data age.** A chart that looks live but is 4 minutes stale is worse than one that
  says so.
- Severity is never communicated by colour alone — always colour + icon + text.
