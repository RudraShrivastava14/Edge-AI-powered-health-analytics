# Setup & Deployment Runbook

Follow this once per developer. Everything here targets the **AWS Free Tier**.

---

## 1. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| AWS CLI | v2 | `aws --version` |
| AWS SAM CLI | 1.100+ | `sam --version` |
| Git | any | `git --version` |
| Docker | optional (for `sam build --use-container`) | `docker --version` |

---

## 2. AWS Account Setup (do this first — Week 1)

1. Create an AWS account (or use an existing one; note the **creation date**, since several
   Free Tier allowances expire 12 months from it).
2. **Enable MFA on the root user**, then stop using root.
3. Create an IAM user (or Identity Center user) for each team member with programmatic
   access and a scoped policy. Never share credentials.
4. **Set a budget guardrail before deploying anything:**
   ```bash
   aws budgets create-budget \
     --account-id "$(aws sts get-caller-identity --query Account --output text)" \
     --budget file://infrastructure/scripts/budget.json \
     --notifications-with-subscribers file://infrastructure/scripts/budget-notifications.json
   ```
5. Enable billing alerts: Billing Console → Billing Preferences → *Receive CloudWatch
   Billing Alerts*.
6. Configure the CLI:
   ```bash
   aws configure --profile healthcloud   # region: ap-south-1, output: json
   export AWS_PROFILE=healthcloud
   ```

---

## 3. Deploy the Cloud Tier

```bash
cd infrastructure
sam build --template cloudformation/template.yaml
sam deploy --guided --stack-name health-analytics-dev \
           --capabilities CAPABILITY_IAM \
           --parameter-overrides Environment=dev AlertEmail=you@example.com
```

Or use the wrapper, which also writes the stack outputs to `infrastructure/.outputs.json`:

```bash
./scripts/deploy.sh dev
```

**Confirm the SNS email subscription** — AWS sends a confirmation link; alerts will not
arrive until you click it.

Record these stack outputs; the edge and frontend both need them:

| Output | Used by |
|---|---|
| `IoTEndpoint` | edge gateway |
| `ApiEndpoint` | frontend |
| `UserPoolId`, `UserPoolClientId` | frontend auth |
| `TelemetryTableName`, `AlertsTableName` | tests, scripts |
| `RawDataBucket`, `WebBucket` | model upload, SPA deploy |

---

## 4. Provision a Device Identity

```bash
cd infrastructure
./scripts/provision_device.sh demo-001
```

This creates an IoT thing, generates an X.509 certificate + key pair, attaches a policy
scoped to that thing's topic only, and writes the material to `edge/config/certs/demo-001/`
(gitignored — **never commit certificates**).

---

## 5. Run the Edge Simulator

```bash
cd edge
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m simulator.run \
  --device-id demo-001 \
  --profile healthy \
  --endpoint "$(jq -r .IoTEndpoint ../infrastructure/.outputs.json)" \
  --cert-dir config/certs/demo-001
```

Profiles: `healthy`, `tachycardia`, `bradycardia`, `arrhythmia`, `hypoxia`, `mixed`.
Add `--dry-run` to print payloads locally without publishing (costs nothing).

Verify arrival: IoT Core Console → *MQTT test client* → subscribe to `hh/v1/+/telemetry`.

---

## 6. Run the Frontend

```bash
cd frontend
npm install
cp .env.example .env      # then fill in the stack outputs
npm run dev               # http://localhost:5173
```

Deploy the built SPA:

```bash
npm run build
aws s3 sync dist/ "s3://$(jq -r .WebBucket ../infrastructure/.outputs.json)/" --delete
aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths '/*'
```

---

## 7. Train and Ship the Model

```bash
cd ai-models
pip install -r requirements.txt
python preprocessing/prepare_mitbih.py --out data/processed
python training/train_autoencoder.py  --data data/processed --epochs 50
python training/quantize.py --model models/autoencoder.keras --out models/edge/autoencoder_int8.tflite
```

Copy the TFLite artefact to the edge device (`edge/edge_inference/models/`) and upload the
full-precision model to S3 for the cloud confirmation Lambda.

---

## 8. Tests

```bash
pip install -r tests/requirements.txt
pytest tests/unit -q                 # no AWS calls
pytest tests/integration -q          # uses moto mocks
pytest tests/integration -q --live   # hits the deployed dev stack (costs quota)
```

---

## 9. Teardown (do this after every benchmarking session)

```bash
cd infrastructure && ./scripts/destroy.sh dev
```

S3 buckets must be emptied before the stack will delete; the script handles that. Verify in
the console that no orphaned resources (log groups, IoT certificates) remain.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| MQTT connect fails with TLS error | Wrong endpoint or missing Amazon root CA | Re-run `provision_device.sh`; check `--endpoint` matches `aws iot describe-endpoint --endpoint-type iot:Data-ATS` |
| Messages publish but no DynamoDB items | IoT Rule SQL or Lambda permission | Check the rule's error action and the Lambda's CloudWatch logs |
| Lambda `AccessDeniedException` | Execution role too narrow | Add the specific action in the template; do not attach `*` |
| 401 from the API | Expired/absent JWT | Re-login in the SPA; confirm the API Gateway authorizer points at the right user pool |
| Cold-start latency spikes | First invocation after idle | Expected; report p50 and p95 separately in benchmarks |
| Unexpected charge appears | A non-free resource was created | Check Cost Explorer *by service*, delete it, note it in the cost log |
