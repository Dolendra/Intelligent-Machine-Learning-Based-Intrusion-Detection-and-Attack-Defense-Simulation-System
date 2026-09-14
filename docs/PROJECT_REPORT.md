# Aegis IDS — Final Project Report

**Full title:** Intelligent Machine-Learning-Based Intrusion Detection and Attack–Defense Simulation System  
**Platform:** Aegis IDS  
**Repository state:** tag **`v2.0-aegis-productionized`** (productionized prototype) · frozen research baseline **`v1.1-research`**  
**Dataset:** CICIDS2017 (`MachineLearningCVE` flow CSVs; not shipped in Git)  
**Stack:** Python · scikit-learn / XGBoost (compared) · SHAP / LIME · FastAPI · React · SQLite  

> **Authoritative sources of truth (prefer these over older Word/PPT drafts):**  
> `models/trained_models/model_metadata.json`, `training_report.json`, `generalization_report.json`, `empirical_mitigation_report.json`, `reports/final_security_validation_report.json`, and the phase docs under `docs/`.  
> Figures: `models/trained_models/figures/`.

---

## Measurement classes (read first)

This report carefully separates three kinds of numbers:

| Class | Meaning | Example |
|-------|---------|---------|
| **Research (IID / temporal)** | Frozen DT/RF scored on CICIDS2017 splits | Binary F1 **0.99048** (IID test) |
| **Simulation assumptions** | Visualization priors in `config.yaml` | DDoS defense efficacy **0.82** |
| **Controlled-lab (P11)** | Measured outcomes on `TestNetworkAdapter` | DDoS `BLOCK_SOURCE` effectiveness **1.00** |

Do **not** treat simulation assumptions as measurements, or IID F1 as a live-network guarantee.

---

## Defensible one-line claim

> **Aegis IDS is a productionized, security-validated intrusion-detection prototype that combines frozen machine-learning detection, explainable risk assessment, controlled response workflows, empirical mitigation experiments, attack-defense simulation, persistence, observability, recovery, and server-enforced authorization, while deliberately maintaining a hard boundary against live network enforcement.**

---

# Chapter 1 — Introduction

Traditional intrusion detection systems often stop at an alert: “attack detected.” Security teams also need *what family of attack*, *why the model decided that*, *how severe the risk is*, and *what defensive action is appropriate*—with clear human control over any response.

Aegis IDS addresses that gap as an **integrated decision-support platform**:

```text
Network flow → preprocess → binary ML → attack family → risk → XAI
→ recommendation → incident → propose / dry-run / approve → CONTROLLED response
→ verification / rollback → attack–defense simulation → SOC UI
```

### Contribution framing

We do **not** claim a novel IDS learning algorithm. The contribution is a **reproducible, end-to-end decision-support and visualization framework** that:

1. Freezes a strong CICIDS2017 research baseline (`v1.1-research`).  
2. Productionizes the application stack through phases **P0–P12** (`v2.0-aegis-productionized`).  
3. Separates **research evaluation**, **simulation assumptions**, and **controlled-lab empirical mitigation**.  
4. Enforces a hard safety boundary: **no live firewall/EDR**, **no automatic unapproved response**.

---

# Chapter 2 — Problem Definition

### Problem statement

Modern SOC workflows require more than a black-box classifier. Gaps in many student / research IDS demos include:

- High benchmark accuracy without honest generalization analysis  
- Little explainability for analyst trust  
- Recommendations disconnected from actionable (but safe) response workflows  
- Simulation that is confused with real mitigation effectiveness  
- Missing authentication, audit, persistence, and fail-safe recovery  

### Objectives

1. Detect malicious vs benign flows with a frozen binary model.  
2. Classify attack families with a frozen multiclass model (attack-only).  
3. Explain predictions (SHAP primary, LIME secondary).  
4. Score risk and emit **advisory** recommendations.  
5. Simulate the attack–defense lifecycle for education and demo.  
6. Provide a **CONTROLLED** response path with approval, verification, and rollback.  
7. Productionize the system (P0–P12) without altering frozen ML artifacts.  
8. Empirically measure mitigation on a controlled lab plane (P11) and validate security boundaries (P12).

### Research questions

| ID | Question |
|----|----------|
| RQ1 | How well can ML distinguish malicious from benign CICIDS2017 flows under an IID split? |
| RQ2 | Which flow features contribute most to detection? |
| RQ3 | Can SHAP/LIME improve interpretability of IDS decisions? |
| RQ4 | Can attack classifications map to actionable (advisory / controlled) defenses? |
| RQ5 | How does performance change under a day-aware temporal holdout? |
| RQ6 | What measurable change occurs when an approved CONTROLLED defense is applied in a lab plane? |

---

# Chapter 3 — Literature / Existing Systems

Intrusion detection research spans **signature-based**, **anomaly-based**, and **machine-learning-based** methods. Signature systems are precise for known patterns but brittle against novelty; ML methods can generalize better but risk false positives and opaque decisions.

**Datasets.** Earlier corpora (e.g., KDD’99 derivatives) are dated. **CICIDS2017** (Sharafaldin et al., 2018) provides labelled flow features for contemporary attack families and remains a standard academic benchmark ([CIC IDS 2017](https://www.unb.ca/cic/datasets/ids-2017.html)).

**ML for IDS.** Tree ensembles and boosting are common on tabular flow features; evaluation should emphasize precision/recall/F1 and PR-AUC under imbalance, not accuracy alone.

**Explainability.** **SHAP** (Lundberg & Lee, 2017) and **LIME** (Ribeiro et al., 2016) support local explanations. In security they aid trust; they do not prove causality.

**SOAR / decision support.** Orchestration maps alerts to playbooks. Aegis adopts this idea at prototype scale: family → recommendation → human-approved response, without unsupervised destructive enforcement.

**Positioning.** Many works isolate either “high CICIDS accuracy” or “dashboard demo.” Aegis integrates detection, multiclass labelling, risk, XAI, controlled response, empirical lab mitigation, simulation, and productionization controls in one reproducible repository.

---

# Chapter 4 — Proposed Aegis IDS Architecture

### Logical layers

```text
React SOC UI
    ↓
FastAPI (auth/RBAC, limits, CORS, observability)
    ↓
ML engine (frozen FeatureBundle + DT + RF) · Risk · SHAP
    ↓
Response service (propose → dry-run → approve → execute → verify → rollback)
    ↓
Adapters: DRY_RUN | CONTROLLED (TestNetworkAdapter) | LIVE (forbidden)
    ↓
Simulation engine (visualization) · SQLite persistence · Ops metrics
```

### Two-stage ML

1. **Binary:** BENIGN vs ATTACK — frozen **Decision Tree**, operating threshold **0.85**  
2. **Multiclass (attack-only):** Bot, BruteForce, DDoS, DoS, PortScan, WebAttack — frozen **Random Forest**

### Provenance tags

| Tag | Meaning |
|-----|---------|
| `v1.1-research` | Frozen academic ML baseline (joblibs + IID metrics) |
| `v2.0-aegis-productionized` | Complete productionized prototype (P0–P12 on `main`) |

Architecture figure: `docs/architecture.png`.

---

# Chapter 5 — Dataset and Data Engineering

### Dataset

- **CICIDS2017** MachineLearningCVE CSVs (~2.83M raw rows before cleaning).  
- Raw files are **not** in Git (size/licensing); place under `MachineLearningCVE/` locally.  
- Label families normalized (e.g., DoS Hulk → DoS).  
- Rare classes with fewer than **50** samples dropped (e.g., Infiltration, Heartbleed) → **~2.52M** usable flows.  
- Stratified split: **70% / 10% / 20%** train / val / test.  

### Split sizes (frozen)

| Split | Rows |
|-------|-----:|
| Train | 1,764,525 |
| Validation | 252,075 |
| Test | 504,151 |

`random_state = 42`, `sample_frac = 1.0`.

### Feature engineering

- Drop leakage/identifier-like columns (Flow ID, IPs, Timestamp, ports where configured).  
- Coerce numeric; remove Inf/NaN/duplicates.  
- **StandardScaler** + **SelectKBest (`f_classif`, k=40)** fit **on train only**.  
- **Dual selectors:** separate SelectKBest for binary vs multiclass (40 features each).  

Artifacts: `feature_bundle.joblib`, `data/processed/*.parquet` (local), `model_metadata.json`.

---

# Chapter 6 — Machine Learning Detection

### Binary model selection (validation ablation)

Candidates shared the same preprocessing. Selection used multi-objective weights (recall 0.30, F1 0.25, PR-AUC 0.20, FPR 0.15, latency 0.10)—**not** highest F1 alone.

| Model | Val F1 | Val Recall | Selection score |
|-------|-------:|-----------:|----------------:|
| logistic_regression | 0.8272 | 0.9706 | 0.9239 |
| **decision_tree** | 0.9905 | **0.9966** | **0.9940** |
| random_forest | 0.9912 | 0.9961 | 0.9877 |
| xgboost | **0.9930** | 0.9899 | 0.9918 |

**Why Decision Tree?** Higher attack **recall** under the IDS-oriented score; XGBoost wins raw F1 but not the selected objective.

### Binary test results (Decision Tree @ 0.85)

| Metric | Value |
|--------|------:|
| Precision | 0.98404 |
| Recall | 0.99700 |
| **F1** | **0.99048** |
| PR-AUC | 0.99744 |
| ROC-AUC | 0.99916 |
| FP / FN | 1,377 / 255 |
| TN / TP | 417,635 / 84,884 |

### Multiclass (attack-only Random Forest) — test

| Metric | Value |
|--------|------:|
| Accuracy | 0.99979 |
| Macro Precision | 0.99762 |
| Macro Recall | 0.99864 |
| **Macro F1** | **0.99813** |
| Weighted F1 | 0.99979 |

Classes: Bot, BruteForce, DDoS, DoS, PortScan, WebAttack.

### Important caveat

These are **IID stratified test** results on CICIDS2017. They demonstrate strong in-dataset discrimination. They are **not** a claim of real-world future performance under live traffic (see Chapters 10–11 and 14).

---

# Chapter 7 — Explainability and Risk

### Explainability

- **SHAP** is the primary local explainer for analyst-facing attributions.  
- **LIME** is secondary / comparative.  
- Explanations support **decision support**, not causal proof of attack mechanics.

### Risk score (configurable)

From `config.yaml` (conceptual blend):

```text
0.50·attack_base + 0.25·confidence·100 + 0.15·intensity·100 + 0.10·asset_criticality
```

Severity bands (project convention): Low / Medium / High / Critical.

### Recommendations

Mapped from attack family and severity to **advisory** actions (monitor, rate-limit, block source, isolate, escalate). Recommendations do **not** automatically change a live network.

---

# Chapter 8 — Attack–Defense Simulation

Simulation is a **safe visualization** of the lifecycle on a simplified enterprise topology:

```text
idle → normal → attack_start → attack_impact → detected → recommended → defended → recovered
```

### Critical honesty

Defense effectiveness values in `config.yaml` are **visualization assumptions**, for example:

| Attack family | Assumed efficacy |
|---------------|-----------------:|
| DDoS | **0.82** |
| DoS | **0.78** |
| PortScan | 0.85 |
| BruteForce | 0.88 |
| WebAttack | 0.90 |
| Bot | 0.92 |

They are **not** empirically measured mitigation rates. Measured lab results appear only in Chapter 11 (P11).

See `docs/05-simulation.md`, `scripts/27_cyber_range_sim_validate.py`.

---

# Chapter 9 — Controlled Response Architecture

### Modes

| Mode | Behavior |
|------|----------|
| `DRY_RUN` | Preview only; `live_network_change = false` |
| `CONTROLLED` | In-memory `TestNetworkAdapter` only |
| `LIVE` | **Forbidden** at propose / adapter layer |

### Lifecycle

```text
propose → dry-run → approve → execute → verify → ACTIVE/VERIFIED
                              ↘ reject
verify failure → rollback
expire / reclaim → safe FAILED (no auto-replay)
```

### RBAC (when auth enabled)

| Role | Propose / dry-run | Approve / rollback |
|------|-------------------|--------------------|
| viewer | no | no |
| analyst | yes | no |
| responder | yes | yes |
| admin | yes | yes |

Role is bound server-side (HMAC bearer / configured API key). Clients cannot escalate via forged `actor` fields.

See `docs/SECURITY_MODEL.md`.

---

# Chapter 10 — Productionization (P0–P12)

Engineering after the research freeze proceeded in sequenced phases on branch `productionization`, merged via PR #2:

| Phase | Focus | Outcome |
|-------|--------|---------|
| P0 | Research baseline freeze | Tag `v1.1-research`; immutable joblibs |
| P1 | PCAP ingestion | Validation, queue, safe reject |
| P2 | Response approval | Propose / dry-run / approve gate |
| P3 | Controlled adapters | `TestNetworkAdapter`; LIVE forbidden |
| P4 | Auth / RBAC | Server-enforced roles |
| P5 | API security | Rate limits, size caps, CORS, headers, WS auth |
| P6 | Persistence | Durable users/actions/audit (Alembic) |
| P7 | Observability | Structured logs, metrics, `/api/ready`, System UI |
| P8 | Performance | Measured envelope; ML not primary bottleneck |
| P9 | Failure recovery / DR | Reclaim without auto-replay; backup/restore |
| P10 | Generalization | Temporal holdout + PSI honesty (`GENERALIZATION.md`) |
| P11 | Empirical mitigation | CONTROLLED lab measurements |
| P12 | Final security validation | Overall **PASS** |

Post-merge verification on `main`: `docs/POST_MERGE_VERIFICATION.md` (**PASS**).  
Release tag: **`v2.0-aegis-productionized`**.

**No phase modified frozen `v1.1-research` model artifacts or published IID metrics.**

---

# Chapter 11 — Empirical Mitigation (P11)

### Purpose

Replace *simulation-only* defense-effectiveness **claims** with **measurements** from an isolated CONTROLLED lab—without removing the simulation, and without connecting real firewall/EDR.

### Protocol (summary)

```text
Controlled synthetic traffic
    → Aegis detection (frozen ML preferred)
    → Conditions: no_defense | recommendation_only | controlled_response
    → Approve → TestNetworkAdapter → traffic_decision gate
    → Measure pre/post windows; repeat N=10
```

### Results (10 repetitions)

| Scenario | No defense / recommendation-only blocked rate | Controlled response | **Measured effectiveness** | Simulation prior | Δ (meas − sim) |
|----------|-----------------------------------------------:|--------------------:|---------------------------:|-----------------:|---------------:|
| DDoS `BLOCK_SOURCE` | 0.00 | **1.00** | **1.00 ± 0** | 0.82 | **+0.18** |
| DoS `RATE_LIMIT` | 0.00 | **0.80** | **0.80 ± 0** | 0.78 | **+0.02** |

### How to cite

> Under the tested controlled environment and scenario, the measured outcome was **1.00** (DDoS block) and **0.80** (DoS rate-limit), with the limitations below. Simulation priors **0.82** / **0.78** remain labelled assumptions and were **not** overwritten.

### Limitations (P11)

- CONTROLLED adapter only — **not** production firewall/EDR effectiveness.  
- In-process synthetic connection attempts, not NIC packets.  
- Hard `BLOCK_SOURCE` yields effectiveness 1.0 by construction of the test gate—validates the measurement framework more than claiming live block rates.  

Full write-up: `docs/EMPIRICAL_MITIGATION.md` (EXP-018 / EXP-019).

---

# Chapter 12 — Security Validation (P12)

P12 did **not** add product features; it validated the closed system.

```text
Authentication/RBAC       PASS
Response safety           PASS
API/input security        PASS
Persistence/recovery      PASS
Model-serving safety      PASS
Simulation isolation      PASS
Empirical mitigation      PASS
Audit integrity           PASS
Production boundary       PASS
Frozen research baseline  PASS

Overall: PASS
```

Artifact: `reports/final_security_validation_report.json`.  
Docs: `FINAL_SECURITY_VALIDATION.md`, `SECURITY_MODEL.md`, `PRODUCTION_READINESS.md`.

Frozen joblib SHA-256[:16] hashes match `model_metadata.json` (`binary_best`, `multiclass_best`, `feature_bundle`).

---

# Chapter 13 — Results and Discussion

### A. Research detection (IID)

Strong discrimination on CICIDS2017 stratified test: binary F1 **0.99048**, multiclass macro-F1 **0.99813**. Residual multiclass confusion (rare) concentrates among PortScan / DoS / WebAttack (`ERROR_ANALYSIS.md`).

### B. Temporal generalization (P10)

| Slice | Binary F1 | Notes |
|-------|----------:|-------|
| IID test | 0.99048 | Official stratified score |
| Friday sample | 0.99770 | Δ F1 (IID−Fri) = **−0.00722**; higher attack rate (~34%) |
| Mon–Thu sample | 0.97997 | Δ F1 = **+0.01051** (degradation) |

Friday multiclass perfect scores cover only **Bot / DDoS / PortScan** present in that sample—not six-class temporal proof.

**IID drift:** no feature with PSI ≥ 0.2 under stratified train→test.  
**Temporal PSI:** max **0.2354** (2 features ≥ 0.2). Wording: *no feature exceeded the PSI threshold in the IID comparison*—**not** “there is no drift.”

### C. Simulation vs empirical

Simulation priors and P11 measurements must be cited **side by side**, never collapsed.

### D. Productionization value

P0–P12 transforms a research classifier pipeline into a **prototype SOC workflow** with auditability, RBAC, fail-safe recovery, and an explicit non-live enforcement boundary—without inflating research metrics.

---

# Chapter 14 — Limitations

1. **Benchmark ≠ production traffic.** CICIDS2017 IID scores do not guarantee live performance.  
2. **No zero-day / unknown-class claim.** Held-out unknown detection is future / separate work.  
3. **External-dataset validation skipped** (compatible CSE-CIC-IDS2018 not present).  
4. **Temporal multiclass incomplete** for BruteForce / DoS / WebAttack on Friday sample.  
5. **Simulation efficacy is assumed**, not measured.  
6. **P11 is a CONTROLLED lab**, not real firewall/EDR.  
7. **No unsupervised live response**; LIVE mode forbidden.  
8. **PCAP path** depends on optional cicflowmeter; without it, extraction is unavailable (fail closed).  
9. **Auth may be off** in research demos; hardened demos should enable it.  
10. **Not an enterprise SOC** (no SLA, no HA cluster claim, no full SOAR integration).

---

# Chapter 15 — Future Work

1. Compatible cross-dataset evaluation under **frozen** preprocessing (no retrain-and-claim).  
2. Broader temporal multiclass coverage across all six families.  
3. Sandbox / opt-in real enforcement adapters **only after** CONTROLLED measurement maturity, with the same approval/verify/rollback model.  
4. Online drift monitoring against live feature streams (beyond IID PSI).  
5. Richer analyst UX / case management while preserving advisory-first defaults.  
6. Optional unknown-class / novelty detection as a **separate** experiment (do not retune the freeze on that holdout).

---

# Chapter 16 — Conclusion

Aegis IDS delivers a coherent story from **detection → explanation → risk → recommendation → controlled response → simulation → productionization**, with reproducible frozen metrics and an explicit safety boundary.

The academically strongest position is:

- Research: strong CICIDS2017 IID and documented temporal evaluation of **frozen** models.  
- Engineering: P0–P12 productionized prototype with P12 security validation **PASS**.  
- Empirics: CONTROLLED-lab mitigation measurements reported **beside** (not replacing) simulation assumptions.  
- Honesty: no live-enforcement claim, no enterprise SLA claim, no zero-day guarantee.

Together, tags **`v1.1-research`** and **`v2.0-aegis-productionized`** provide clear provenance for examination, demonstration, and viva.

---

# References

1. I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, “Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization,” *ICISSP*, 2018.  
2. Canadian Institute for Cybersecurity, “Intrusion Detection Evaluation Dataset (CIC-IDS2017),” University of New Brunswick. https://www.unb.ca/cic/datasets/ids-2017.html  
3. S. M. Lundberg and S.-I. Lee, “A Unified Approach to Interpreting Model Predictions,” *NeurIPS*, 2017.  
4. M. T. Ribeiro, S. Singh, and C. Guestrin, “‘Why Should I Trust You?’ Explaining the Predictions of Any Classifier,” *KDD*, 2016.  
5. T. Chen and C. Guestrin, “XGBoost: A Scalable Tree Boosting System,” *KDD*, 2016.  
6. R. Sommer and V. Paxson, “Outside the Closed World: On Using Machine Learning for Network Intrusion Detection,” *IEEE S&P*, 2010.  
7. A. L. Buczak and E. Guven, “A Survey of Data Mining and Machine Learning Methods for Cyber Security Intrusion Detection,” *IEEE Communications Surveys & Tutorials*, 2016.  
8. H.-J. Liao et al., “Intrusion Detection System: A Comprehensive Review,” *JNCA*, 2013.  
9. D. Gunning and D. Aha, “DARPA’s Explainable Artificial Intelligence (XAI) Program,” *AI Magazine*, 2019.  
10. N. Moustafa and J. Slay, “UNSW-NB15…,” *MilCIS*, 2015.  

*(Add institution-required citation style and any guide-mandated papers.)*

---

# Team Contribution

Suggested three-member ownership (everyone should still understand the full pipeline for viva)—see `docs/TEAM.md`:

| Member focus | Primary ownership |
|--------------|-------------------|
| **ML / Data** | CICIDS loading, features, training, IID/temporal metrics, notebooks |
| **Security intelligence** | SHAP/LIME, risk, recommendations, incidents, response safety narrative |
| **Application / simulation** | FastAPI, React SOC UI, simulation engine, demo ops, Docker |

Repository / release: Nelluri Dolendra Sai Teja — GitHub `Dolendra` · tags `v1.1-research`, `v2.0-aegis-productionized`.

*(Replace with your institution’s exact author list and contribution percentages as required.)*

---

# Appendices

### A. Artifact index (selected)

| Artifact | Path |
|----------|------|
| Model metadata | `models/trained_models/model_metadata.json` |
| Training report | `models/trained_models/training_report.json` |
| Generalization (P10) | `models/trained_models/generalization_report.json` · `docs/GENERALIZATION.md` |
| Empirical (P11) | `models/trained_models/empirical_mitigation_report.json` · `docs/EMPIRICAL_MITIGATION.md` |
| Security validation (P12) | `reports/final_security_validation_report.json` |
| Post-merge verification | `docs/POST_MERGE_VERIFICATION.md` |
| Demo script | `docs/DEMO.md` |
| Viva Q&A | `docs/VIVA_QA.md` |

### B. Figures to insert in Word/LaTeX

- `binary_confusion_matrix.png`, `binary_roc.png`, `feature_importance.png`  
- `multiclass_confusion_matrix.png`  
- `temporal_*.png` (Friday holdout)  
- `drift_psi_train_vs_test.png`  
- Architecture: `docs/architecture.png`

### C. How to regenerate key reports

```bash
python scripts/41_generalization_report.py
python scripts/42_empirical_mitigation_experiment.py --repetitions 10
python scripts/43_final_security_validation.py
```

---

*End of final project report (repository-aligned, v2.0-aegis-productionized).*
