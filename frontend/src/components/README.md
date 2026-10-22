# Components

Reusable presentational components. No data fetching, no routing — props in, UI out.

| Component | Purpose |
|---|---|
| `VitalCard` | Single vital with current value, unit, trend arrow, and normal-range context |
| `ECGChart` | Renders a decoded raw window; used in the alert evidence view |
| `TimeSeriesChart` | HR/SpO2/temp over a time range; must handle gaps from offline periods |
| `AlertBadge` | Severity indicator — colour + icon + text label |
| `DeviceStatus` | Online/offline pill with last-seen relative time |
| `TimeRangePicker` | 1 h / 24 h / 7 d / 30 d / custom |
| `EmptyState`, `ErrorState`, `LoadingSkeleton` | The three non-happy paths, standardised |
