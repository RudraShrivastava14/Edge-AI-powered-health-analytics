# Literature Survey

**Cloud-Based Wearable Health Analytics Platform using Edge–Cloud Intelligence**

Scope: peer-reviewed work at the intersection of (a) wearable/IoT health monitoring
architectures, (b) edge and fog computing for healthcare, (c) machine learning for
physiological anomaly detection, and (d) serverless computing for IoT backends.

> **Note for the team:** the entries below are the canonical, widely-cited works in this
> area and form the backbone of the survey. Before submission, each member must (i) pull
> the actual PDF, (ii) verify the summary against the paper, and (iii) add 3–5 recent
> (2023+) papers from IEEE Xplore / ACM DL / PubMed in their own area. Add every citation
> to `references.bib`.

---

## 1. Survey Method

- **Databases searched:** IEEE Xplore, ACM Digital Library, ScienceDirect, PubMed, arXiv.
- **Query strings:** `("wearable" OR "IoT") AND ("health monitoring") AND ("edge computing"
  OR "fog computing")`; `("ECG" OR "physiological") AND ("anomaly detection" OR
  "autoencoder")`; `"serverless" AND ("IoT" OR "healthcare")`.
- **Inclusion criteria:** English, peer-reviewed or high-citation preprint, published
  2016–2025, reports either a system architecture or a quantitative evaluation.
- **Exclusion criteria:** purely clinical studies with no computational contribution;
  papers without evaluation.

---

## 2. Thematic Areas

### Theme A — IoT/Cloud Architectures for Health Monitoring

| Ref | Work | Contribution | Limitation relevant to us |
|---|---|---|---|
| [1] | Islam et al., *The Internet of Things for Health Care: A Comprehensive Survey*, IEEE Access, 2015 | Foundational taxonomy of IoT healthcare: sensing, network, service, application layers; catalogues topologies and platforms | Pre-dates practical edge ML; cloud-centric; no cost analysis |
| [2] | Baker, Xiang & Atkinson, *Internet of Things for Smart Healthcare: Technologies, Challenges and Opportunities*, IEEE Access, 2017 | Proposes a generic end-to-end IoT healthcare framework; identifies energy, security, and interoperability as open issues | Framework is conceptual; not deployed or measured |
| [3] | Rahmani et al., *Exploiting smart e-Health gateways at the edge of healthcare IoT: A fog computing approach*, FGCS, 2018 | Demonstrates a "smart gateway" fog layer performing local processing, data compression, and embedded storage | Uses dedicated on-premise gateway hardware; no public-cloud integration or elasticity |

### Theme B — Edge / Fog Intelligence

| Ref | Work | Contribution | Limitation relevant to us |
|---|---|---|---|
| [4] | Shi et al., *Edge Computing: Vision and Challenges*, IEEE IoT Journal, 2016 | Defines the edge-computing paradigm and its latency/bandwidth/privacy motivations | Vision paper; no health-specific instantiation |
| [5] | Satyanarayanan, *The Emergence of Edge Computing*, IEEE Computer, 2017 | Cloudlet model; argues for tiered compute placement | Conceptual; no split-inference design |
| [6] | Kang et al., *Neurosurgeon: Collaborative Intelligence Between the Cloud and Mobile Edge*, ASPLOS, 2017 | Automatically partitions a DNN between mobile and cloud at the optimal layer to minimise latency/energy | Partitions a *single* network; assumes continuous connectivity; not an anomaly-triggered cascade |
| [7] | Teerapittayanon et al., *Distributed Deep Neural Networks over the Cloud, the Edge and End Devices*, ICDCS, 2017 | DDNN with early-exit branches: easy samples exit at the edge, hard ones escalate | Evaluated on vision, not physiological time series; no deployment-cost analysis |

### Theme C — ML for Physiological Anomaly Detection

| Ref | Work | Contribution | Limitation relevant to us |
|---|---|---|---|
| [8] | Moody & Mark, *The impact of the MIT-BIH Arrhythmia Database*, IEEE EMB Magazine, 2001 | The reference annotated ECG corpus used by nearly all subsequent work | Dataset paper; small subject count, clinical (not wearable) recording conditions |
| [9] | Hannun et al., *Cardiologist-level arrhythmia detection and classification in ambulatory ECG using a deep neural network*, Nature Medicine, 2019 | 34-layer CNN matching cardiologist performance on 12 rhythm classes over single-lead ambulatory ECG | Model is far too large for a microcontroller/Pi; inference assumed offline/server-side |
| [10] | Rajpurkar et al., *Cardiologist-Level Arrhythmia Detection with Convolutional Neural Networks*, arXiv, 2017 | Large-scale single-lead CNN; establishes the deep-learning baseline for ECG | Same scale problem; no streaming/edge constraint |
| [11] | Chauhan & Vig, *Anomaly detection in ECG time signals via deep long short-term memory networks*, IEEE DSAA, 2015 | LSTM predictive model; anomalies flagged from prediction-error distribution — a *semi-supervised* formulation needing only normal data | Recurrent model is expensive on-device; no system integration |
| [12] | Malhotra et al., *LSTM-based Encoder-Decoder for Multi-sensor Anomaly Detection*, ICML Anomaly Detection Workshop, 2016 | Reconstruction-error anomaly detection for multivariate sensor streams — the template for our autoencoder | Not quantised or deployed; offline evaluation only |
| [13] | Schirrmeister et al. / Kiranyaz et al., *Real-Time Patient-Specific ECG Classification by 1-D Convolutional Neural Networks*, IEEE TBME, 2016 | Compact 1-D CNN suitable for real-time, patient-specific classification | Requires per-patient labelled data; no cloud tier |

### Theme D — Serverless & Cost-Efficient Cloud Backends

| Ref | Work | Contribution | Limitation relevant to us |
|---|---|---|---|
| [14] | Jonas et al., *Cloud Programming Simplified: A Berkeley View on Serverless Computing*, Tech. Report, 2019 | Defines serverless, its economics, and its limitations (state, cold starts, data locality) | General-purpose; no IoT/health case study |
| [15] | Baldini et al., *Serverless Computing: Current Trends and Open Problems*, 2017 | Survey of FaaS platforms and patterns | Predates most managed IoT-to-FaaS integrations |
| [16] | Persson & Angelsmark, *Kappa / serverless at the edge* line of work; and Aslanpour et al., *Serverless Edge Computing: Vision and Challenges*, ACSW, 2021 | Argues for FaaS abstractions spanning edge and cloud | Vision-level; no concrete healthcare pipeline with measured cost |

### Theme E — Privacy, Security and Regulation

| Ref | Work | Contribution | Limitation relevant to us |
|---|---|---|---|
| [17] | Kaissis et al., *Secure, privacy-preserving and federated machine learning in medical imaging*, Nature Machine Intelligence, 2020 | Survey of federated learning, differential privacy, secure aggregation in medicine | Imaging-focused; heavy cryptographic machinery unsuitable for a Pi-class device |
| [18] | McMahan et al., *Communication-Efficient Learning of Deep Networks from Decentralized Data* (FedAvg), AISTATS, 2017 | Federated averaging — train without centralising raw data | Assumes many participating clients and a coordination server; out of scope for a semester project but noted as future work |

---

## 3. Comparative Summary

| Aspect | Cloud-only IoT health systems [1–3] | Edge/fog systems [3–7] | Deep ECG models [9–13] | **This project** |
|---|---|---|---|---|
| Where inference runs | Cloud | Edge (usually only) | Offline / server | **Edge screen + cloud confirm (cascade)** |
| Uplink volume | Full raw stream | Reduced, fixed policy | N/A | **Adaptive, anomaly-triggered** |
| Model size constraint | None | Considered | Ignored | **INT8 TFLite, < 500 KB, measured** |
| Backend model | VMs / containers | On-prem gateway | N/A | **Fully serverless (FaaS)** |
| Cost reported | Rarely | Rarely | Never | **Explicit Free Tier budget + per-1000-device projection** |
| Reproducible IaC | No | No | No | **Yes — one-command CloudFormation/SAM deploy** |
| End-to-end latency measured | Sometimes | Sometimes | No | **Yes, p95 target < 5 s, X-Ray traced** |

---

## 4. Takeaways that shaped our design

1. **Reconstruction-error anomaly detection [11][12] is the right formulation** for wearable
   data, because labelled abnormal data is scarce but normal data is abundant. This directly
   motivates the autoencoder in `ai-models/`.
2. **Early-exit / cascaded inference [6][7] is proven in vision but under-explored for
   physiological streams.** Porting that idea is our main technical contribution.
3. **Compact 1-D CNNs [13] are viable on ARM-class hardware**, so an edge model is realistic
   — but published work stops at the model and does not carry it into a deployed system.
4. **Serverless economics [14] are a genuinely good match for bursty IoT**, yet almost no
   health-IoT paper quantifies deployment cost. Reporting a real bill is a differentiator.
5. **Privacy improves as a side effect** of not uploading raw waveforms — a point [17] makes
   in principle and our architecture realises in practice.

---

## 5. References

See [`references.bib`](references.bib) for BibTeX entries. Numbering in this document
matches the keys there.
