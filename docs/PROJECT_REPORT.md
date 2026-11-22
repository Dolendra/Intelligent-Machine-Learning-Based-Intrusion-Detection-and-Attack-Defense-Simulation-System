# Aegis IDS — Final Project Report

**Full title:** Intelligent Machine-Learning-Based Intrusion Detection and Attack–Defense Simulation System  
**Platform:** Aegis IDS  
**Repository state:** tag **`v2.0-aegis-productionized`** (productionized prototype) · frozen research baseline **`v1.1-research`** · open-set research track and pre-registered R3 campaign on `main` (Chapter 13)  
**Datasets:** CICIDS2017 (`MachineLearningCVE` flow CSVs; not shipped in Git) · CSE-CIC-IDS2018 for external validation (research track; not shipped in Git)  
**Stack:** Python · scikit-learn / XGBoost (compared) · SHAP / LIME · FastAPI · React · SQLite  

> **Authoritative sources of truth (prefer these over older Word/PPT drafts):**  
> `models/trained_models/model_metadata.json`, `training_report.json`, `generalization_report.json`, `empirical_mitigation_report.json`, `reports/final_security_validation_report.json`, and the phase docs under `docs/`.  
> Research track (Chapter 13): `docs/research/RESULTS.md`, `docs/research/R3_RESULTS.md`, `docs/research/EVIDENCE_RELIABILITY_STUDY.md` and the artifacts they name.  
> Figures: `models/trained_models/figures/`.

---

> **Phase 2 research-integrity corrections (2026-11-18).** Older figures are kept and relabelled, not deleted.
> * The binary "test results (Decision Tree @ 0.85)" were computed at the argmax threshold **0.5** (ML-1). Deployed-threshold
>   figures come from `research_artifacts/v11_reeval/v11_test_metrics_by_threshold.json`.
> * The family macro-F1 0.99813 assumes a perfect first stage (ML-2). End-to-end, at 0.85 the system detects 57.1 % of Bot and
>   37.3 % of WebAttack test flows (`research_artifacts/v11_reeval/v11_family_end_to_end.json`).
> * The P10 Friday "temporal" result is **superseded (contaminated)**: about 70 % of the scored Friday rows were training rows (ML-3).
> * P11 "measured" mitigation values hold by construction; they validate the harness, not mitigation (ML-12).
> * Full record: `docs/research/RESEARCH_INTEGRITY_REPORT.md`.

## Measurement classes (read first)

This report carefully separates three kinds of numbers:

| Class | Meaning | Example |
|-------|---------|---------|
| **Research (IID)** | Frozen DT/RF scored on the CICIDS2017 random test split | Binary F1 **0.99048** @ 0.5 (argmax); **0.99382** @ 0.85 (deployed) |
| **Simulation assumptions** | Visualization priors in `config.yaml` | DDoS defense efficacy **0.82** |
| **Controlled-lab (P11)** | Harness validation on `TestNetworkAdapter` (deterministic by construction) | DDoS `BLOCK_SOURCE` 1.00 *by construction* — not a mitigation measurement |
| **Research (open-set)** | Aegis-OSR and the R3 campaign: unseen-family and cross-network detection at a fixed benign false-alarm rate, seed-level statistics | LOAFO zero-day recall **0.706** at α = 1 % (Chapter 13) |

Do **not** treat simulation assumptions as measurements, or IID F1 as a live-network guarantee.

---

## Defensible one-line claim

> **Aegis IDS is a productionized, security-validated intrusion-detection prototype that combines frozen machine-learning detection, explainable risk assessment, controlled response workflows, empirical mitigation experiments, attack-defense simulation, persistence, observability, recovery, and server-enforced authorization, while deliberately maintaining a hard boundary against live network enforcement. Its research track measures, with pre-registered statistics, when fusing supervised and novelty evidence helps zero-day detection (in distribution, for all six models tested) and when it hurts (after cross-network recalibration).**

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
5. Adds an **open-set research track** (Aegis-OSR, Chapter 13): a conformal zero-day gate beside the frozen models, and a pre-registered multi-model campaign that reports where fusion helps and where it fails, including negative results.

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
9. Measure unseen-family (zero-day) detection at a bounded false-alarm rate, and its behaviour under temporal and cross-network shift (research track).

### Research questions

| ID | Question |
|----|----------|
| RQ1 | How well can ML distinguish malicious from benign CICIDS2017 flows under an IID split? |
| RQ2 | Which flow features contribute most to detection? |
| RQ3 | Can SHAP/LIME improve interpretability of IDS decisions? |
| RQ4 | Can attack classifications map to actionable (advisory / controlled) defenses? |
| RQ5 | How does performance change under a day-aware temporal holdout? |
| RQ6 | What measurable change occurs when an approved CONTROLLED defense is applied in a lab plane? |
| RQ7 | Does fusing supervised and benign-novelty evidence detect unseen attack families better than the classifier alone at the same benign false-alarm rate? |
| RQ8 | Does that gain, and the false-alarm guarantee, survive temporal and cross-network (CSE-CIC-IDS2018) shift? |

---

# Chapter 3 — Literature / Existing Systems

Intrusion detection research spans **signature-based**, **anomaly-based**, and **machine-learning-based** methods. Signature systems are precise for known patterns but brittle against novelty; ML methods can generalize better but risk false positives and opaque decisions.

**Datasets.** Earlier corpora (e.g., KDD’99 derivatives) are dated. **CICIDS2017** (Sharafaldin et al., 2018) provides labelled flow features for contemporary attack families and remains a standard academic benchmark ([CIC IDS 2017](https://www.unb.ca/cic/datasets/ids-2017.html)).

**ML for IDS.** Tree ensembles and boosting are common on tabular flow features; evaluation should emphasize precision/recall/F1 and PR-AUC under imbalance, not accuracy alone.

**Explainability.** **SHAP** (Lundberg & Lee, 2017) and **LIME** (Ribeiro et al., 2016) support local explanations. In security they aid trust; they do not prove causality.

**Open-set and zero-day detection.** Closed-set classifiers cannot reject what they never saw (Sommer & Paxson, 2010); open-set recognition formalises this (Scheirer et al., 2013), and nearest-neighbour distances are a strong out-of-distribution score (Sun et al., 2022). Conformal prediction turns any score into a p-value with a finite-sample false-alarm bound under exchangeability (Vovk et al., 2005; Bates et al., 2023). Recent work already shows that conformal recalibration under shift restores the false-alarm rate but not detection (Şahin & Mert, 2026); Chapter 13 builds on that rather than claiming it.

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

- Drop identifier-like columns where present (Flow ID, IPs, Timestamp). **Destination Port is kept and is a model feature** (possible shortcut; ML-10).  
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

### Binary test results (Decision Tree) — both operating points

The historical table was headed "@ 0.85" but was computed at the argmax threshold 0.5 (ML-1). Both columns below are the same
frozen model on the same test split; 0.85 was chosen on the validation split, so the test split selected nothing.

| Metric | @ 0.5 (argmax; historical figure) | @ 0.85 (deployed) |
|--------|------:|------:|
| Precision | 0.98404 | 0.99549 |
| Recall | 0.99700 | 0.99217 |
| **F1** | **0.99048** | **0.99382** |
| FPR | 0.00329 | 0.00091 |
| PR-AUC | 0.99744 | 0.99744 (threshold-free) |
| ROC-AUC | 0.99916 | 0.99916 (threshold-free) |
| FP / FN | 1,377 / 255 | 383 / 667 |
| TN / TP | 417,635 / 84,884 | 418,629 / 84,472 |

Source: `research_artifacts/v11_reeval/v11_test_metrics_by_threshold.json` (the 0.5 column reproduces `model_metadata.json` exactly).

### Multiclass (attack-only Random Forest) — test

| Metric | Value |
|--------|------:|
| Accuracy | 0.99979 |
| Macro Precision | 0.99762 |
| Macro Recall | 0.99864 |
| **Macro F1** | **0.99813** |
| Weighted F1 | 0.99979 |

Classes: Bot, BruteForce, DDoS, DoS, PortScan, WebAttack.

**This table assumes a perfect first stage** (the family model is applied to every true attack row). End-to-end at the deployed
0.85 threshold, the two-stage system detects and correctly names **57.1 % of Bot** (n = 389) and **36.8 % of WebAttack** (n = 429)
test flows; other families are ≥ 99.4 %. The end-to-end 7-class macro-F1 is **0.881** at 0.85 (0.890 at 0.5).
Source: `research_artifacts/v11_reeval/v11_family_end_to_end.json`.

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

| Scenario | No defense / recommendation-only blocked rate | Controlled response | **Harness value (by construction)** | Simulation prior | Δ (not meaningful) |
|----------|-----------------------------------------------:|--------------------:|---------------------------:|-----------------:|---------------:|
| DDoS `BLOCK_SOURCE` | 0.00 | **1.00** | **1.00 ± 0** | 0.82 | **+0.18** |
| DoS `RATE_LIMIT` | 0.00 | **0.80** | **0.80 ± 0** | 0.78 | **+0.02** |

### How to cite

> **Corrected (ML-12):** these values are **harness validation, deterministic by construction** (a hard block passes 0 % by design and the rate limiter allows 20 %). They are not mitigation-effectiveness measurements, and the measured−simulation deltas are not meaningful. Historical wording: "the measured outcome was **1.00** (DDoS block) and **0.80** (DoS rate-limit)". Simulation priors **0.82** / **0.78** remain labelled assumptions and were **not** overwritten.

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

# Chapter 13 — Open-Set Zero-Day Research (Aegis-OSR) and the Pre-Registered R3 Campaign

> **Measurement class: Research (open-set).** Every number in this chapter is read from a versioned research artifact
> (named under each table) or from the generated paper numbers (`docs/research/paper_numbers.json`). The frozen v1.1
> models are never retrained or modified; the research detector runs beside them.

### 13.1 Motivation

Chapters 5–6 evaluate a **closed-set** detector: every flow is forced into *benign* or one of the families seen in
training. A never-seen attack family is therefore either called benign or given a wrong known label (Sommer & Paxson,
2010). The research track asks two questions the IID evaluation cannot answer:

1. Can unseen attack families be detected while the benign false-alarm rate stays at a chosen budget?
2. What happens to detection and to that budget when the network changes?

### 13.2 Method: Aegis-OSR

| Step | What it does |
|---|---|
| Supervised evidence | `1 − P(BENIGN)` for the flow, from an XGBoost classifier over benign + known families |
| Novelty evidence | Mean distance of the flow to its `k = 5` nearest **benign** training flows (kNN out-of-distribution score; Sun et al., 2022) |
| Benign surprisal | Each evidence score is converted to a benign tail probability on a benign calibration split |
| Fisher fusion | The two surprisals are added, so a flow that is moderately unusual to both streams outranks one that is mildly odd to either |
| Split-conformal calibration | The fused score becomes a p-value on a disjoint benign split; alert if `p ≤ α`. The benign false-alarm rate is bounded by `α` **only when test benign traffic is exchangeable with the calibration traffic** (Vovk et al., 2005; Bates et al., 2023) |
| Attribution | Mondrian (per-family) conformal p-values separate *known family*, `UNKNOWN-ATTACK` and `ZERO-DAY-ANOMALY` |
| Adaptation without retraining | `recal@W`: re-estimate the calibration on `W` confirmed-benign flows from the new environment |

**Integration.** In the application, Aegis-OSR runs as an **advisory Zero-Day Gate**. The frozen v1.1 detector stays the
decision authority (`zero_day_gate.incident_policy: frozen`); gate alerts are recorded and listed for analyst review.
On 82,111 flows held out from both models, the benign incident rate is 0.077 % for the frozen policy, 0.896 % for the
gate alone and 0.934 % for the union (`research_artifacts/v11_reeval/v11_policy_alert_rates.json`).

### 13.3 Evaluation protocols

| Protocol | Train / calibrate | Evaluate | Question |
|---|---|---|---|
| **LOAFO** (leave one attack family out) | CICIDS2017 with one family removed | The removed family as a true zero-day | Does fusion detect unseen families? |
| **Temporal** | CICIDS2017 Mon–Thu | Thursday / Friday | Does the false-alarm budget survive day-to-day drift? |
| **Cross-dataset** | CICIDS2017 | CSE-CIC-IDS2018 | Does anything transfer to a new network? |
| **Cross per day** | CICIDS2017, recalibrated on each 2018 day's first 2,000 benign flows | The rest of that day | Does same-day recalibration restore detection? |
| **Cross-dataset LOAFO** | CICIDS2017 with family F removed | 2018 days that contain F | Does the LOAFO gain transfer to a new network? |

The temporal protocol is a true day-ordered split. It replaces the contaminated P10 slice (Chapter 14 B).

### 13.4 Development results (seeds 1–5)

| Finding | Value | Source |
|---|---|---|
| LOAFO zero-day recall at `α = 1 %`, Aegis-OSR | **0.706** [0.689, 0.723], realised benign FPR 1.00 % | `research_artifacts/openset_loafo_summary.json` |
| Same, closed-set XGBoost alone / v1.1-style decision tree | 0.490 / 0.241 | same |
| Gain over the same classifier | **+0.216** [+0.180, +0.252], paired *t* over seeds *p* = 7.6×10⁻⁵, positive on 5 of 5 seeds | same |
| Temporal, Mon–Thu → Friday: realised FPR | **7.09 %** (budget 1 %) | `research_artifacts/openset_temporal_summary.json` |
| CICIDS2017 → CSE-CIC-IDS2018: Aegis-OSR realised FPR | **36.7 %** | `research_artifacts/openset_cross_summary_v2.json` |
| Frozen v1.1 binary model on CSE-CIC-IDS2018 | F1 **0.278** (precision 0.988, recall 0.162) vs IID F1 0.990 | `research_artifacts/frozen_v11_on_cic2018_v2.json` |
| Per-day recalibration (`recal@2000`) on 2018 | Mean FPR 1.62 %, but known-family recall only 0.088 | paper numbers (`FactPdRecal2000*`) |
| After recalibration: Fisher fusion − same XGBoost | **−0.237** conformal recall, 0 of 5 seeds positive; the gap persists at a matched 1 % FPR | paper numbers (`FactRaPdFisherXgbConf*`) |

**Reading.** In distribution, fusion clearly helps. Under shift, the false-alarm guarantee breaks, recalibration brings
the false-alarm rate back but not detection, and the fused score then detects *fewer* known attacks than its own
classifier.

**Novelty position (stated honestly).** That recalibration restores the false-alarm rate but not detection has already
been published (Şahin & Mert, 2026). The project does not claim it. The remaining observation is narrower: *at a matched
false-alarm rate, a fusion rule that helps in distribution can hurt after cross-network recalibration.*

### 13.5 Pre-registered campaign (R3, Phases 4–8)

To test whether these effects are general or specific to one XGBoost model, a confirmatory campaign was pre-registered
before any result existed (`docs/research/R3_AMENDMENT.md`) and run after approval.

| Design item | Value |
|---|---|
| Evidence models | XGBoost (v3 reference), decision tree, random forest, extra trees, XGBoost (defaults), LightGBM |
| Seeds | 101–105 (new; the seed is the statistical unit) |
| Protocols | LOAFO, temporal, cross per day, cross-dataset LOAFO |
| Records | 780 (130 per model) |
| Primary metric | Detection rate at an exactly matched 1 % benign FPR (oracle-matched, for comparison only) |
| Statistics | Paired *t*-test over seeds with Holm correction across the 6 models; hierarchical bootstrap 95 % intervals (10,000 replicates) |
| Pre-registered protocol fixes | Randomised (smoothed) conformal p-values, frozen configurations, unified method names, feature-only leakage report |

**Verdicts** (Δ = Fisher fusion − the same evidence model alone; source
`research_artifacts/r3/analysis/campaign/hypotheses.json` and `reliability.json`):

| ID | Hypothesis | Result | Verdict |
|---|---|---|---|
| A4 | Validity: realised FPR at `α = 1 %` stays in [0.8, 1.2] % | 24 of 24 model × method cells, 0.990 %–1.061 % | **Supported** |
| A1 | LOAFO: fusion raises zero-day detection | **6 of 6** models, +0.134 to +0.268 | **Supported** |
| A2 | The evidence model matters | Decision tree −0.173 vs the XGBoost reference (Holm *p* = 2.0×10⁻⁵) | **Supported** |
| A5 | 2018 per day, after recalibration: fusion lowers known-attack detection | Same direction for **6 of 6** models, −0.212 to −0.006 | **Supported** |
| A6 | 2018 cross-dataset LOAFO: does the LOAFO gain transfer? | 0 models significantly positive, 1 significantly negative (random forest) | **Setting- and model-dependent** (no transfer) |
| A7 | Max fusion is a safe fixed alternative (non-inferior within 0.02) | 0 of 6 models | **Rejected** |
| RS1 | A benign-only screen predicts stream reliability | Spearman ρ = −0.16 [−0.51, +0.27] | **Rejected** |
| RS2 | The screen predicts when fusion hurts | Spearman ρ = +0.20 [−0.30, +0.62] | **Rejected** |

**Per model** (mean over seeds 101–105, hierarchical 95 % interval):

| Evidence model | A1 LOAFO gain | A5 2018 per-day change |
|---|---|---|
| XGBoost (v3 ref.) | +0.228 [+0.08, +0.42] | −0.212 [−0.44, −0.03] |
| Decision tree | +0.268 [+0.06, +0.51] | −0.006 [−0.10, +0.08] |
| Random forest | +0.134 [+0.04, +0.25] | −0.126 [−0.28, +0.00] |
| Extra trees | +0.214 [+0.07, +0.38] | −0.055 [−0.18, +0.02] |
| XGBoost (defaults) | +0.247 [+0.10, +0.43] | −0.181 [−0.40, −0.02] |
| LightGBM | +0.154 [+0.06, +0.26] | −0.187 [−0.40, −0.03] |

**Phase 7 (new method): not built.** The pre-registered rule allowed a gated method only if both RS1 and RS2 were
supported. Both were rejected: the benign-only screen flags 62 %–100 % of benign warm-up flows on every 2018 day, so it
cannot tell good days from bad ones (`docs/research/EVIDENCE_RELIABILITY_STUDY.md`). This negative result is reported,
not hidden.

**Phase 8 validation** (`research_artifacts/r3/validation/campaign_validation.json`):
* A1, A5 and A6 keep their verdicts when any single family or day is dropped. A7 becomes inconclusive when one 2018 day
  is dropped.
* The XGBoost LOAFO gain replicates on the new seeds: +0.218 (seeds 1–5, matched-FPR re-analysis) → +0.228 (seeds
  101–105), inside the earlier interval.
* Matched-FPR and conformal-recall results agree in sign for 6 of 6 models on A1 and A5.
* Smoothed p-values remove a tie artefact: the decision tree alone realises 0.10 % FPR with deterministic p-values
  versus 1.01 % with smoothed ones at `α = 1 %`.

**Exploratory lead (not a finding).** Refreshing the kNN *reference set* with the warm-up benign flows
(`recal+ref@2000`) makes Fisher − B positive for 5 of 6 models on both 2018 protocols. This points at the stale benign
reference as the main cause of the loss. It came from the same campaign, so it needs its own pre-registered test.

### 13.6 What the research supports and does not support

| Supported | Not supported or not tested |
|---|---|
| In distribution, fixed fusion of supervised and kNN benign-novelty evidence improves zero-day detection at a matched false-alarm rate for six different tree-based models | That the gain transfers to unseen families on a new network (A6: it does not) |
| After cross-network recalibration, the same fusion loses known-attack detection relative to its own classifier (direction consistent across six models) | A benign-only rule for choosing between fusion and the classifier under shift (RS1/RS2 rejected) |
| Neither fixed rule (Fisher or max) is safe to keep under shift | Neural (TabM), CatBoost, CLOSR or tuned models: not run |
| The calibration is valid in distribution (A4) | Universal zero-day detection, or a guaranteed false-alarm rate under distribution shift |

### 13.7 Engineering outputs of the research track

* **Modular framework** (`framework/`): typed detector, open-set, adapter, explainer and policy modules with a registry.
  The default pipeline is decision-identical to the service (`docs/FRAMEWORK.md`).
* **API and UI:** `/api/framework/*`, `/api/research/r3`, the Zero-Day Lab and the Research Lab "R3 campaign" tab.
* **Integrity tooling:** a protected-artifact manifest, a regression gate that proves the frozen v1.1 files equal the
  tag, scripts that refuse to overwrite historical outputs, and generated paper numbers that forbid hand-typed results.
* **Release validation** (`scripts/75_release_validation.py`): security, integrity, framework parity and R3 gates in one
  versioned report (`reports/release/release_validation_20261122_phase11b.json`: PASS).
* **Papers:** `docs/research/Aegis_OSR_paper_ieee.pdf` (IEEE format) and `docs/research/Aegis_Research_Paper.docx`.

---

# Chapter 14 — Results and Discussion

### A. Research detection (IID)

Strong discrimination on the CICIDS2017 random test split: binary F1 **0.99382** at the deployed 0.85 (0.99048 at argmax 0.5); stage-2 macro-F1 **0.99813** given a perfect stage 1. At 0.85 the system misses 42.9 % of Bot and 62.7 % of WebAttack flows. Residual multiclass confusion (rare) concentrates among PortScan / DoS / WebAttack (`ERROR_ANALYSIS.md`).

### B. Temporal generalization (P10) — SUPERSEDED (contaminated)

> **Do not cite.** Script 25 re-scored raw day CSVs without excluding training rows; the training split was a random split
> across all days, so about 70 % of the Friday rows were training rows (ML-3). The values below are kept as a historical record
> only. The valid temporal evaluation is the research track's day-ordered protocol (`docs/research/RESULTS.md`, Mon–Thu→Fri).

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

### E. Open-set research (Chapter 13)

The IID scores in A do not survive a change of network: the frozen binary model's F1 falls from 0.990 to **0.278** on CSE-CIC-IDS2018. In distribution, Aegis-OSR detects **0.706** of unseen-family flows at a 1 % false-alarm rate versus 0.490 for the same classifier alone, and the pre-registered campaign shows this gain for **all six** tree-based evidence models. Under cross-network shift the picture reverses: after recalibration the fused detector finds *fewer* known attacks than its own classifier for all six models, the gain does not transfer to unseen families on the new network, and a benign-only screen could not predict when fusion hurts. These negative results are part of the contribution: they show exactly where a fixed fusion rule stops being safe.

---

# Chapter 15 — Limitations

1. **Benchmark ≠ production traffic.** CICIDS2017 IID scores do not guarantee live performance.  
2. **Zero-day detection is measured, not guaranteed.** The LOAFO gain (Chapter 13) is an in-distribution result on six held-out CICIDS2017 families; it does **not** transfer to unseen families on CSE-CIC-IDS2018 (A6). No universal zero-day claim.  
3. **The false-alarm bound is conditional.** It holds only while test benign traffic is exchangeable with calibration traffic; under drift it reached 7.09 % (Friday) and 36.7 % (CSE-CIC-IDS2018) at a 1 % budget. Recalibration restores the rate on average but not detection.  
4. **Temporal multiclass incomplete** for BruteForce / DoS / WebAttack on Friday sample.  
5. **Simulation efficacy is assumed**, not measured.  
6. **P11 is a CONTROLLED lab**, not real firewall/EDR.  
7. **No unsupervised live response**; LIVE mode forbidden.  
8. **PCAP path** depends on optional cicflowmeter; without it, extraction is unavailable (fail closed).  
9. **Auth may be off** in research demos; hardened demos should enable it.  
10. **Not an enterprise SOC** (no SLA, no HA cluster claim, no full SOAR integration).  
11. **Research scope.** The R3 campaign used six CPU tree models with library defaults and five seeds. TabM, CLOSR, CatBoost and tuned models were not run; independent confirmation datasets (NF-v3, LycoS) were not used (download and licence holds).

---

# Chapter 16 — Future Work

1. A pre-registered confirmatory test of the **reference-refresh** lead (Chapter 13.5), then confirmation on independent data (NF-v3, LycoS once licensing allows).  
2. Broader temporal multiclass coverage across all six families.  
3. Sandbox / opt-in real enforcement adapters **only after** CONTROLLED measurement maturity, with the same approval/verify/rollback model.  
4. Online drift monitoring against live feature streams (beyond IID PSI).  
5. Richer analyst UX / case management while preserving advisory-first defaults.  
6. A label-free way to choose between fusion and the supervised stream under shift; the benign-only screen tested here failed (RS1/RS2), so a different signal is needed.  
7. The GPU campaign (TabM, CLOSR) and an equal-budget tuning study across evidence models.

---

# Chapter 17 — Conclusion

Aegis IDS delivers a coherent story from **detection → explanation → risk → recommendation → controlled response → simulation → productionization**, with reproducible frozen metrics and an explicit safety boundary.

The academically strongest position is:

- Research: strong CICIDS2017 IID evaluation of **frozen** models (the P10 temporal evaluation is superseded; see Chapter 14 B).  
- Engineering: P0–P12 productionized prototype with P12 security validation **PASS**.  
- Empirics: CONTROLLED-lab mitigation measurements reported **beside** (not replacing) simulation assumptions.  
- Open-set research: fusion improves zero-day detection in distribution for all six models tested, but loses detection after cross-network recalibration; both effects were confirmed in a pre-registered campaign, and the proposed reliability screen was rejected and reported as such.  
- Honesty: no live-enforcement claim, no enterprise SLA claim, no zero-day guarantee.

Together, tags **`v1.1-research`** and **`v2.0-aegis-productionized`**, and the research track on `main` (release validation PASS, `reports/release/`), provide clear provenance for examination, demonstration, and viva.

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
11. W. J. Scheirer et al., “Toward Open Set Recognition,” *IEEE TPAMI*, 2013.  
12. Y. Sun et al., “Out-of-Distribution Detection with Deep Nearest Neighbors,” *ICML*, 2022.  
13. V. Vovk, A. Gammerman, and G. Shafer, *Algorithmic Learning in a Random World*, Springer, 2005.  
14. S. Bates et al., “Testing for Outliers with Conformal p-Values,” *Annals of Statistics*, 2023.  
15. F. Şahin and N. S. Mert, “Dual-Threshold Conformal Deferral for Trustworthy Security Alert Triage,” *Electronics*, vol. 15, no. 18, art. 4084, 2026, doi:10.3390/electronics15184084.  
16. Canadian Institute for Cybersecurity, “CSE-CIC-IDS2018 on AWS,” University of New Brunswick. https://www.unb.ca/cic/datasets/ids-2018.html  

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
| Aegis-OSR method and development results | `docs/research/AEGIS_OSR.md` · `docs/research/RESULTS.md` |
| R3 pre-registration and results | `docs/research/R3_AMENDMENT.md` · `docs/research/R3_RESULTS.md` · `research_artifacts/r3/analysis/campaign/` |
| Reliability study (Phase 6–7) | `docs/research/EVIDENCE_RELIABILITY_STUDY.md` |
| Papers | `docs/research/Aegis_OSR_paper_ieee.pdf` · `docs/research/Aegis_Research_Paper.docx` |
| Release validation | `reports/release/release_validation_20261122_phase11b.json` |

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
python scripts/74_r3_analysis.py --run campaign_b campaign_c --name <new_name> --assign xgb_ref=campaign_b dt=campaign_b rf=campaign_b et=campaign_c xgb=campaign_c lgbm=campaign_c
python scripts/75_release_validation.py --tag <tag>
```

---

*End of final project report (repository-aligned: v2.0-aegis-productionized plus the open-set research track and R3 campaign).*
