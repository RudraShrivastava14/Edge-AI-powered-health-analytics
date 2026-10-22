# Architecture Documentation

| File | Contents |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Full design document: component view, data flows, ADRs, NFRs, security, failure modes |
| [`API_CONTRACT.md`](API_CONTRACT.md) | MQTT telemetry payload schema and the REST API contract |
| [`diagrams/`](diagrams/) | Source files for every diagram (Mermaid `.mmd`) + exported PNG/SVG |

## Diagram policy

Diagrams are written as **Mermaid source** so they are diffable and reviewable in pull
requests. GitHub renders `.mmd` fenced blocks inline. Export to PNG/SVG only for the slide
deck and the written report — keep the source as the master copy.

Export:

```bash
npx @mermaid-js/mermaid-cli -i diagrams/system-architecture.mmd -o diagrams/system-architecture.png -s 3
```

Or paste into <https://mermaid.live> for a quick render.
