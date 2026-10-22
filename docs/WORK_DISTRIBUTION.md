# Work Distribution

**Project:** Cloud-Based Wearable Health Analytics Platform using Edge–Cloud Intelligence
**Course:** Cloud Computing
**Last updated:** 2026-07-31

---

## 1. Team

| # | Name | Reg. No. | Role | Code | Share |
|---|------|----------|------|------|-------|
| 1 | **Krish Agarwal** | 23BIT0427 | Cloud Infrastructure, DevOps, Backend & Data | `KA` | **~45 %** |
| 2 | **Monis Raza** | 23BIT228 | AI/ML & Edge Intelligence | `MR` | ~30 % |
| 3 | **Rudra Srivastav** | 23BIT174 | Frontend, Visualisation & Documentation | `RS` | ~25 % |

### Folder ownership

| Member | Owns |
|---|---|
| **Krish Agarwal (KA)** | `infrastructure/`, `backend/`, `database/`, `.github/workflows/`, `docs/aws/`, `tests/` |
| **Monis Raza (MR)** | `ai-models/`, `edge/`, `dataset/` |
| **Rudra Srivastav (RS)** | `frontend/`, `docs/` (survey & report), `results/`, `presentation/` |

Shared: code review (every PR needs one approval from a member who did not author it), the
root `README.md`, and demo rehearsal.

### Why the split is uneven

The project has four distinct technical areas but three members, so Krish covers **two** of
them — the cloud infrastructure tier and the backend/data tier. These are the most tightly
coupled parts of the system: the CloudFormation template, the Lambda functions, and the
DynamoDB schema all have to change together, so splitting them across two people would
create constant merge friction on the same files.

That gives Krish 16 of the 32 tasks; Monis and Rudra own 8 each.

---

## 2. Detailed Task Allocation

### Krish Agarwal (KA) — Cloud Infrastructure, DevOps, Backend & Data

**2a. Infrastructure & DevOps**

| ID | Task | Deliverable | Status |
|---|---|---|---|
| I-1 | AWS account setup, IAM users, MFA, budget + billing alarm at $1 | Account runbook in `docs/setup/SETUP.md` | ☐ |
| I-2 | Author the SAM/CloudFormation template for the full stack | `infrastructure/cloudformation/template.yaml` | ☐ |
| I-3 | IoT Core: thing type, policy, X.509 certificate provisioning script | `infrastructure/scripts/provision_device.sh` | ☐ |
| I-4 | Least-privilege IAM roles per Lambda | `docs/aws/IAM_NOTES.md` | ☐ |
| I-5 | CI/CD: GitHub Actions with OIDC federation to AWS, `sam deploy` on merge to `main` | `.github/workflows/deploy.yml` | ☐ |
| I-6 | CloudWatch dashboards, log-retention policies (7 days), alarms | Dashboard JSON + screenshots in `results/` | ☐ |
| I-7 | Free Tier quota tracking; weekly cost report | `docs/aws/FREE_TIER_BUDGET.md` | ☐ |
| I-8 | S3 + CloudFront static hosting for the SPA, cache invalidation on deploy | Template section + deploy script | ☐ |

**2b. Backend & Data**

| ID | Task | Deliverable | Status |
|---|---|---|---|
| B-1 | Define and validate the telemetry message schema | `backend/common/schema.py`, `docs/architecture/API_CONTRACT.md` | ☐ |
| B-2 | `ingest_handler` Lambda: validate, normalise, fan out to DynamoDB + S3 | `backend/lambdas/ingest_handler/` | ☐ |
| B-3 | `anomaly_processor` Lambda: cloud-side confirmation inference | `backend/lambdas/anomaly_processor/` | ☐ |
| B-4 | `alert_dispatcher` Lambda: dedupe/debounce, publish to SNS | `backend/lambdas/alert_dispatcher/` | ☐ |
| B-5 | `api_handler` Lambda + API Gateway routes (`/vitals`, `/alerts`, `/devices`) | `backend/lambdas/api_handler/`, OpenAPI spec | ☐ |
| B-6 | DynamoDB single-table design, GSIs, TTL policy | `database/schemas/` | ☐ |
| B-7 | Cognito user pool integration + JWT authorizer wiring | Template section + `backend/api/` | ☐ |
| B-8 | Integration tests with `moto`; load test harness | `tests/integration/` | ☐ |

**Also owns:** end-to-end system integration and keeping the deployed stack inside the AWS
Free Tier.

### Monis Raza (MR) — AI/ML & Edge Intelligence

| ID | Task | Deliverable | Status |
|---|---|---|---|
| M-1 | Acquire and document MIT-BIH, PTB-XL, WESAD; write download scripts | `dataset/`, `ai-models/preprocessing/` | ☐ |
| M-2 | Preprocessing pipeline: filtering, resampling to 125 Hz, windowing, normalisation | `ai-models/preprocessing/` | ☐ |
| M-3 | Baseline models (threshold rules, isolation forest) for comparison | `ai-models/notebooks/01_baselines.ipynb` | ☐ |
| M-4 | 1-D convolutional autoencoder; train, tune reconstruction-error threshold | `ai-models/training/train_autoencoder.py` | ☐ |
| M-5 | INT8 post-training quantisation → TFLite; verify accuracy delta < 2 % | `ai-models/models/`, conversion script | ☐ |
| M-6 | Edge inference runtime + store-and-forward MQTT publisher | `edge/edge_inference/`, `edge/simulator/` | ☐ |
| M-7 | Cloud-side confirmation model (larger, non-quantised) packaged for Lambda | `ai-models/models/cloud/` | ☐ |
| M-8 | Model evaluation: precision, recall, F1, ROC-AUC, confusion matrices | `results/benchmarks/model_eval.md` | ☐ |

### Rudra Srivastav (RS) — Frontend, Visualisation & Documentation

| ID | Task | Deliverable | Status |
|---|---|---|---|
| F-1 | React + Vite app scaffold, routing, theming (light/dark) | `frontend/` | ☐ |
| F-2 | Cognito-backed login/logout flow | `frontend/src/services/auth.js` | ☐ |
| F-3 | Live vitals view (HR, SpO₂, temperature) with polling updates | `frontend/src/pages/LiveVitals.jsx` | ☐ |
| F-4 | Historical trends: time-range picker, aggregate charts | `frontend/src/pages/Trends.jsx` | ☐ |
| F-5 | Alert timeline + acknowledgement action | `frontend/src/pages/Alerts.jsx` | ☐ |
| F-6 | Device management view (register/deactivate a device) | `frontend/src/pages/Devices.jsx` | ☐ |
| F-7 | Literature survey + research-gap documents | `docs/literature-survey/` | ☐ |
| F-8 | Architecture diagrams, final report, slide deck, demo script | `docs/architecture/`, `presentation/` | ☐ |

---

## 3. Timeline (12-week plan)

| Week | Milestone | Owner |
|---|---|---|
| 1 | Problem finalisation, literature survey | RS (all contribute) |
| 2 | Architecture design, repo scaffold, work split | KA (all contribute) |
| 3 | AWS account, IAM, billing alarms, IoT Core skeleton | KA |
| 4 | Telemetry schema + `ingest_handler` + DynamoDB tables | KA |
| 5 | Dataset acquisition + preprocessing pipeline | MR |
| 6 | Edge simulator publishing to IoT Core end-to-end | MR + KA |
| 7 | Autoencoder training + quantisation | MR |
| 8 | Anomaly processor + SNS alerting path | KA |
| 9 | REST API + Cognito auth | KA + RS |
| 10 | Dashboard: live view, trends, alerts | RS |
| 11 | Benchmarking, elasticity demo, cost analysis | KA + MR |
| 12 | Report, slides, demo rehearsal, submission | All |

---

## 4. Collaboration Conventions

- **Branching:** `main` (protected) ← `dev` ← `feature/<initials>-<short-desc>`
  (e.g. `feature/ka-ingest-lambda`, `feature/mr-autoencoder`, `feature/rs-live-vitals`)
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `infra:`, `test:`)
- **PRs:** must state which task ID they close; require one non-author approval
- **Issues:** one GitHub issue per task ID above, labelled by area
- **Stand-up:** async written update in the team channel, twice weekly
- **Secrets:** never committed — use AWS Systems Manager Parameter Store and GitHub Actions
  OIDC. `.env` and all certificates are gitignored.

---

## 5. Contribution Ledger (fill in before submission)

| Member | Reg. No. | Tasks owned | Commits | PRs merged | Reviews given | Contribution |
|---|---|---|---|---|---|---|
| Krish Agarwal | 23BIT0427 | 16 (I-1…I-8, B-1…B-8) | | | | **~45 %** |
| Monis Raza | 23BIT228 | 8 (M-1…M-8) | | | | ~30 % |
| Rudra Srivastav | 23BIT174 | 8 (F-1…F-8) | | | | ~25 % |

Fill the commit/PR/review columns from GitHub Insights before submitting:
`Insights → Contributors`.
