# System Architecture

**Cloud-Based Wearable Health Analytics Platform using Edge–Cloud Intelligence**

---

## 1. Architectural Style

The platform is a **three-tier, event-driven, serverless architecture** with **split
inference** across the edge and cloud tiers.

| Tier | Responsibility | Deployment |
|---|---|---|
| **Edge tier** | Acquisition, signal conditioning, first-pass anomaly screening, adaptive uplink | Raspberry Pi gateway or Python simulator |
| **Cloud tier** | Ingestion, confirmation inference, persistence, alerting, query API | AWS managed services (Free Tier) |
| **Presentation tier** | Clinician/user dashboard | React SPA on S3 + CloudFront |

Guiding principles:

1. **No always-on servers.** Every compute unit is a Lambda invoked by an event. This is
   what keeps the bill at zero and is the core cloud-computing lesson of the project.
2. **Move computation to the data, not data to the computation.** The edge decides what is
   worth uploading.
3. **Everything is infrastructure-as-code.** The stack can be destroyed and recreated with
   one command.
4. **Fail safe, not silent.** If the uplink is down, the edge buffers; if the model is
   uncertain, the event escalates to the cloud rather than being dropped.

---

## 2. Component Architecture

```mermaid
flowchart TB
    subgraph EDGE["Edge Tier — Device / Gateway"]
        direction TB
        SENS["Sensor layer<br/>ECG · PPG-HR · SpO₂ · Temp · IMU"]
        COND["Signal conditioning<br/>bandpass 0.5–40 Hz · resample 125 Hz<br/>motion-artefact rejection using IMU"]
        WIN["Windowing<br/>10 s windows, 50% overlap"]
        TFL["TFLite INT8 autoencoder<br/>reconstruction error e"]
        POL["Uplink policy engine<br/>e < τ_low  → summary only<br/>τ_low ≤ e < τ_high → summary + downsampled window<br/>e ≥ τ_high → summary + full window (priority)"]
        BUF["Store-and-forward buffer<br/>SQLite ring, survives offline"]
        MQ["MQTT client (TLS 1.2, X.509)"]
        SENS --> COND --> WIN --> TFL --> POL --> BUF --> MQ
    end

    subgraph CLOUD["Cloud Tier — AWS"]
        direction TB
        IOT["IoT Core broker<br/>topic: hh/v1/{deviceId}/telemetry"]
        RULE["IoT Rule<br/>SELECT * FROM 'hh/v1/+/telemetry'"]
        L1["λ ingest_handler"]
        DDBT[("DDB: Telemetry<br/>PK device#id | SK ts<br/>TTL 30 d")]
        S3R[("S3: raw-windows/<br/>year/month/day/device/")]
        L2["λ anomaly_processor<br/>Keras confirmation model"]
        DDBA[("DDB: Alerts<br/>PK device#id | SK ts<br/>GSI: status-index")]
        L3["λ alert_dispatcher<br/>dedupe + debounce 5 min"]
        SNS["SNS topic: health-alerts"]
        APIGW["API Gateway HTTP API<br/>JWT authorizer"]
        L4["λ api_handler"]
        DDBD[("DDB: Devices<br/>PK device#id")]
        COG["Cognito User Pool"]
        CW["CloudWatch Logs / Metrics / Alarms"]

        IOT --> RULE --> L1
        L1 --> DDBT
        L1 --> S3R
        L1 -->|"flag ∈ {suspect, critical}"| L2
        L2 --> DDBA
        L2 --> L3
        L3 --> SNS
        APIGW --> L4
        L4 --> DDBT
        L4 --> DDBA
        L4 --> DDBD
        COG -.validates.-> APIGW
    end

    subgraph UI["Presentation Tier"]
        SPA["React SPA<br/>S3 + CloudFront"]
    end

    MQ -->|"MQTT/TLS 8883"| IOT
    SPA -->|"HTTPS + Bearer JWT"| APIGW
    SPA -.login.-> COG
    SNS -->|"email / SMS"| USR["Caregiver / Clinician"]
    L1 -.-> CW
    L2 -.-> CW
    L3 -.-> CW
    L4 -.-> CW
```

---

## 3. Data Flow — Normal Path

```mermaid
sequenceDiagram
    autonumber
    participant D as Wearable
    participant G as Edge Gateway
    participant I as IoT Core
    participant L1 as λ ingest_handler
    participant DB as DynamoDB
    participant S3 as S3

    loop every 10 s window
        D->>G: raw samples (125 Hz)
        G->>G: filter → window → TFLite inference
        alt reconstruction error < τ_low  (≈95% of windows)
            G->>I: compact summary (~200 B JSON)
        else τ_low ≤ error
            G->>I: summary + encoded window (~2 KB)
        end
    end
    I->>L1: IoT Rule invocation (batched)
    L1->>L1: schema validation + unit normalisation
    L1->>DB: PutItem Telemetry (TTL = now + 30 d)
    opt window attached
        L1->>S3: PutObject raw-windows/…/window.npz.gz
    end
```

## 4. Data Flow — Anomaly Path

```mermaid
sequenceDiagram
    autonumber
    participant G as Edge Gateway
    participant I as IoT Core
    participant L1 as λ ingest_handler
    participant L2 as λ anomaly_processor
    participant DB as DynamoDB
    participant L3 as λ alert_dispatcher
    participant SNS as SNS
    participant U as Caregiver

    G->>I: summary + full window, flag=critical (QoS 1)
    I->>L1: rule invocation
    L1->>L2: async invoke (event payload + S3 key)
    L2->>L2: full-precision model inference + rule cross-check
    alt confirmed anomaly
        L2->>DB: PutItem Alerts{severity, confidence, evidence}
        L2->>L3: async invoke
        L3->>L3: dedupe (same device+class within 5 min?)
        L3->>SNS: Publish
        SNS->>U: email / SMS  ⟵ target: < 5 s from sample
    else false positive
        L2->>DB: PutItem Telemetry{edge_fp: true}
        Note over L2,DB: logged as hard-negative for<br/>the next retraining round
    end
```

---

## 5. Deployment View

```mermaid
flowchart LR
    subgraph LOCAL["Developer machine"]
        SAM["AWS SAM CLI"]
    end
    subgraph GH["GitHub"]
        REPO["Repository"]
        GA["GitHub Actions<br/>(OIDC → AWS role)"]
    end
    subgraph REGION["AWS Region: ap-south-1"]
        CFN["CloudFormation stack<br/>health-analytics-{env}"]
        subgraph RES["Provisioned resources"]
            R1["IoT Core things + policies"]
            R2["4 × Lambda + layers"]
            R3["3 × DynamoDB tables"]
            R4["2 × S3 buckets"]
            R5["API Gateway + Cognito"]
            R6["SNS + CloudWatch"]
        end
    end
    SAM --> CFN
    REPO --> GA --> CFN
    CFN --> RES
```

Environments: `dev` (per-developer, destroyed nightly) and `prod` (the demo stack).
Stack names are parameterised so both can coexist in one account without collision.

---

## 6. Key Design Decisions (ADR summary)

| # | Decision | Alternatives considered | Why |
|---|---|---|---|
| ADR-1 | Lambda for all compute | EC2 t2.micro, ECS Fargate | EC2 free tier expires at 12 months and is always-on; Lambda's free tier is perpetual and matches bursty IoT traffic |
| ADR-2 | DynamoDB as the hot store | RDS PostgreSQL, Timestream, InfluxDB on EC2 | 25 GB always-free; key design `PK=device#id, SK=timestamp` serves every read pattern we have; Timestream has no perpetual free tier |
| ADR-3 | IoT Core instead of raw API Gateway ingest | HTTP POST → API Gateway | Per-device X.509 identity, MQTT keep-alive on a lossy link, QoS 1 delivery, Rules Engine routing — all managed |
| ADR-4 | Split inference (edge screen + cloud confirm) | Cloud-only inference; edge-only inference | Cloud-only wastes bandwidth and the message quota; edge-only cannot host a high-capacity model on a Pi. The cascade gets edge latency with cloud accuracy |
| ADR-5 | TFLite INT8 quantisation | Full FP32 Keras, ONNX Runtime, pruning only | ~4× smaller, ~3× faster on ARM CPU, accuracy delta measured and reported in `results/` |
| ADR-6 | S3 + CloudFront for the SPA | Amplify Hosting, EC2 + nginx | Cheapest and simplest; Amplify Hosting's free tier is 12-month limited |
| ADR-7 | 30-day TTL on telemetry items | Keep forever | Keeps DynamoDB inside the 25 GB always-free limit; older data is already archived to S3 |
| ADR-8 | Single-region (`ap-south-1`) | Multi-region active-active | Multi-region cross-region traffic is billable and out of scope; DR strategy documented instead |

---

## 7. Non-Functional Requirements

| NFR | Target | How verified |
|---|---|---|
| End-to-end alert latency | < 5 s (p95) from sample to SNS publish | X-Ray traces + timestamp deltas, `results/benchmarks/latency.md` |
| Edge inference latency | < 50 ms per 10 s window on Pi 4 | `timeit` harness on device |
| Ingestion throughput | ≥ 50 msg/s sustained (50 simulated devices) | Load test in `tests/integration/load_test.py` |
| Uplink reduction | ≥ 90 % vs. stream-everything baseline | Byte counters in the simulator |
| Availability | Best-effort; edge buffers ≥ 6 h offline | Chaos test: disconnect network, verify replay |
| Monthly cost | $0 within Free Tier at demo scale | AWS Cost Explorer screenshot |
| Security | TLS in transit, SSE-S3/KMS at rest, least-privilege IAM, no secrets in repo | `docs/aws/IAM_NOTES.md`, `gitleaks` in CI |
| Privacy | No PII in telemetry; device IDs are opaque UUIDs | Schema review |

---

## 8. Security Architecture

- **Device identity:** each device gets a unique X.509 certificate; the IoT policy scopes
  publish permission to `hh/v1/${iot:Connection.Thing.ThingName}/telemetry` only, so a
  compromised device cannot spoof another.
- **User identity:** Cognito User Pool; API Gateway validates the JWT before any Lambda
  runs. `api_handler` additionally checks that the caller is authorised for the requested
  `deviceId`.
- **Data at rest:** SSE-S3 on buckets, encryption-at-rest enabled on DynamoDB.
- **Least privilege:** each Lambda has its own execution role scoped to the exact tables
  and prefixes it touches.
- **Secrets:** none in the repository; GitHub Actions authenticates via OIDC role
  assumption, and runtime configuration comes from SSM Parameter Store.
- **Log hygiene:** telemetry payloads are not logged at INFO; only IDs and metrics.

---

## 9. Scalability & Elasticity

- Lambda scales horizontally with concurrent IoT events; reserved concurrency caps are set
  to protect the Free Tier quota from a runaway simulator.
- DynamoDB is on-demand: no capacity planning, scales with traffic.
- The elasticity demo (Objective O8) replays 1 → 50 → 200 simulated devices and captures
  the `ConcurrentExecutions` and `Duration` CloudWatch metrics to show automatic scaling
  with no configuration change.

---

## 10. Failure Modes

| Failure | Detection | Mitigation |
|---|---|---|
| Network loss at edge | MQTT disconnect callback | SQLite ring buffer, exponential-backoff reconnect, batched replay |
| Lambda throttle / error | CloudWatch alarm on `Errors`, `Throttles` | SQS dead-letter queue on async invocations; retry with backoff |
| Malformed payload | JSON-schema validation in `ingest_handler` | Reject to a `quarantine/` S3 prefix, emit metric, never crash the handler |
| Alert storm | Count of alerts per device per minute | `alert_dispatcher` debounces to at most 1 notification per device per class per 5 min |
| Model drift | Rising cloud-side false-positive rate | Hard negatives logged for periodic retraining; threshold τ is configurable via SSM without redeploying the edge |
| Free Tier breach | AWS Budget alarm at $1 | Email alert + documented teardown script |
