# AWS Free Tier Budget & Quota Plan

**Goal:** run the entire platform at **$0/month** for the duration of the project.

> ⚠️ AWS Free Tier allowances change. Every number below must be re-verified against
> <https://aws.amazon.com/free/> before the final report, and a screenshot of the actual
> Cost Explorer bill placed in `results/`.

---

## 1. Service-by-Service Allowance vs. Planned Usage

| Service | Free Tier allowance | Type | Planned usage (demo scale) | Headroom |
|---|---|---|---|---|
| **AWS IoT Core** | 250 000 messages/month (first 12 months) | 12-mo | 5 devices × 6 msg/min × 43 200 min ≈ **~130 000/mo** | ~48 % used |
| **AWS Lambda** | 1 M requests + 400 000 GB-seconds/month | **Always free** | ~200 000 invocations, 128–512 MB, ~200 ms avg ≈ **~15 000 GB-s** | < 5 % used |
| **DynamoDB** | 25 GB storage, 25 WCU + 25 RCU | **Always free** | ~2 GB with 30-day TTL; on-demand mode | Large |
| **Amazon S3** | 5 GB Standard, 20 000 GET, 2 000 PUT/month (first 12 months) | 12-mo | ~1 GB raw windows + model artefacts + SPA build | ~20 % used |
| **API Gateway (HTTP API)** | 1 M requests/month (first 12 months) | 12-mo | Dashboard polling ~50 000/mo | < 5 % used |
| **Amazon Cognito** | 10 000 MAUs (user pools) | **Always free** | < 10 users | Negligible |
| **Amazon SNS** | 1 M publishes, 1 000 email notifications/month | **Always free** (email) | < 500 alerts/mo | Fine |
| **CloudWatch** | 10 custom metrics, 10 alarms, 5 GB log ingestion/month | **Always free** | Set log retention to **7 days**; keep custom metrics ≤ 10 | Watch this one |
| **CloudFront** | 1 TB egress, 10 M requests/month | **Always free** | < 1 GB | Negligible |
| **AWS X-Ray** | 100 000 traces recorded/month | **Always free** | Sample at 5 % | Fine |
| **SQS (DLQs)** | 1 M requests/month | **Always free** | Near zero | Fine |
| **SSM Parameter Store** | Standard parameters free | Always free | ~10 parameters | Fine |
| **CloudFormation** | Free for AWS resource types | Always free | — | — |

### Deliberately avoided (no usable free tier / easy to overrun)

| Service | Why avoided | What we use instead |
|---|---|---|
| Amazon Timestream | No perpetual free tier; write-heavy pricing | DynamoDB with TTL + S3 |
| Amazon Kinesis Data Streams | Shard-hours billed continuously | IoT Core Rules → Lambda |
| Amazon SageMaker endpoints | Real-time endpoints are billed per instance-hour | Model packaged inside a Lambda layer |
| Amazon RDS | Free tier expires at 12 months, always-on | DynamoDB |
| NAT Gateway | ~$32/month, never free | Lambdas run outside a VPC |
| Amazon MSK / Managed Prometheus / OpenSearch | No free tier | CloudWatch |
| Amazon QuickSight | Trial only | Charts rendered in the React SPA |

---

## 2. The Three Real Risks

1. **IoT Core message quota.** This is the binding constraint. At 1 message/second per
   device, five devices would consume ~13 M messages/month — 50× over. The **edge
   summarisation policy is what makes the project fit**: one summary every 10 s per device.
   Do not remove it, and cap the simulator's publish rate.
2. **CloudWatch log ingestion.** Verbose logging in a hot Lambda burns the 5 GB allowance
   fast. Set `RetentionInDays: 7` on every log group and log at `INFO`, not `DEBUG`, in
   `prod`. Never log full payloads.
3. **The 12-month clock.** IoT Core, S3, and API Gateway allowances expire 12 months after
   account creation. Note the account creation date in the team channel and prefer the
   always-free services in any design change.

---

## 3. Guardrails (implement in Week 1)

- [ ] **AWS Budgets:** monthly cost budget of **$1** with an email alert at 50 % and 100 %.
- [ ] **Billing alerts** enabled in the account preferences.
- [ ] **Lambda reserved concurrency** capped (e.g. 10 per function) so a runaway simulator
      cannot exhaust the request quota.
- [ ] **S3 lifecycle rule:** transition `raw-windows/` to Standard-IA at 30 days, expire at
      90 days.
- [ ] **DynamoDB TTL** enabled on the telemetry table (30-day attribute).
- [ ] **CloudWatch log retention** set to 7 days on all log groups (in the SAM template
      globals, so no group is missed).
- [ ] **Teardown script** (`infrastructure/scripts/destroy.sh`) — run it after every
      benchmarking session and before any long break.
- [ ] **Cost Explorer** checked weekly; record the figure in the table below.

---

## 4. Weekly Cost Log

| Week | Date | MTD cost | Notes |
|---|---|---|---|
| 1 | | $0.00 | Account setup only |
| 2 | | | |
| 3 | | | |
| … | | | |

---

## 5. Beyond Free Tier — Cost Projection (for the report)

Estimating on-demand `ap-south-1` list prices, to be filled in with verified figures during
Week 11:

| Scale | IoT messages/mo | Lambda invocations/mo | DynamoDB writes/mo | S3 storage | Est. monthly cost |
|---|---|---|---|---|---|
| 5 devices (demo) | ~130 K | ~200 K | ~200 K | ~1 GB | **$0 (Free Tier)** |
| 100 devices | ~2.6 M | ~4 M | ~4 M | ~20 GB | _to be computed_ |
| 1 000 devices | ~26 M | ~40 M | ~40 M | ~200 GB | _to be computed_ |

Also compute, for contrast, the **stream-everything baseline** at the same device counts —
the ratio between the two is the headline economic result of the project (RQ4).

---

## 6. Reference Links

- AWS Free Tier: <https://aws.amazon.com/free/>
- AWS Pricing Calculator: <https://calculator.aws/>
- IoT Core pricing: <https://aws.amazon.com/iot-core/pricing/>
- Lambda pricing: <https://aws.amazon.com/lambda/pricing/>
- DynamoDB pricing: <https://aws.amazon.com/dynamodb/pricing/on-demand/>
