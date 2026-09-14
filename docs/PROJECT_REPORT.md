# Intelligent ML-Based Intrusion Detection and Attack–Defense Simulation System

**Platform name:** Aegis IDS  
**Dataset:** CICIDS2017 (`MachineLearningCVE`)  
**Stack:** Python · Scikit-learn / XGBoost (compared) · SHAP / LIME · FastAPI · React · SQLite  
**Frozen models (v1.1):** Binary **Decision Tree** @ threshold **0.85** · Multiclass **Random Forest** (attack-only)

> Use this document as the backbone of your major-project report. Copy sections into Word/LaTeX and insert figures from `models/trained_models/figures/`. Authoritative metrics: `models/trained_models/model_metadata.json` and `training_report.json`.

---

## 1. Abstract

This project presents an integrated intelligent intrusion detection platform that goes beyond raw classifier accuracy. The system detects malicious network flows, classifies attack families, estimates risk, explains predictions with SHAP (primary) and LIME (secondary), recommends advisory defensive actions, and interactively simulates the attack-to-defense lifecycle on a simplified enterprise topology. On CICIDS2017, the frozen binary Decision Tree achieves test F1 **0.99048** and ROC-AUC **0.99916** (threshold 0.85); the frozen attack-only Random Forest multiclass model achieves macro-F1 **0.99813** and weighted-F1 **0.99979**. A day-aware Friday temporal holdout scores the same frozen artifacts without retraining and is reported separately from the IID split (§8). These benchmark results are not claims of real-world future performance under live traffic.

---

## 2. Introduction & motivation

Traditional IDS outputs often stop at “attack detected.” Analysts also need *what*, *why*, *how severe*, and *what to do*. This project bridges **detection** and **security decision support** through an end-to-end pipeline:

```text
Traffic → Features → Binary ML → Attack family → Risk → XAI → Recommendation → Simulation → Dashboard
```

### Contribution framing (defensible)

We do **not** claim a novel IDS algorithm. The contribution is an **integrated decision-support and visualization framework** for ML-based intrusion detection.

---

## 3. Research questions

| ID | Question |
|----|----------|
| RQ1 | How effectively can ML distinguish malicious from benign flows? |
| RQ2 | Which flow features contribute most to detection? |
| RQ3 | Can XAI (SHAP/LIME) improve interpretability of IDS predictions? |
| RQ4 | Can attack classifications map to actionable defensive recommendations? |
| RQ5 | Can simulation improve understanding of the attack–defense lifecycle? |

---

## 4. Related work

Intrusion detection research broadly spans **signature-based**, **anomaly-based**, and **machine-learning-based** approaches. Signature systems are precise for known patterns but brittle against novel attacks; anomaly and ML methods generalize better but can raise false positives and suffer from opaque decisions.

**Datasets.** Many classic corpora (e.g., KDD Cup’99 derivatives) are outdated relative to modern traffic. Sharafaldin et al. introduced **CICIDS2017**, a labelled flow dataset covering benign activity and contemporary attack families (DoS/DDoS, brute force, web attacks, botnet, infiltration, Heartbleed), generated to address diversity and realism gaps in earlier benchmarks ([Sharafaldin et al., 2018](https://www.scitepress.org/Papers/2018/66398/66398.pdf); [CIC IDS 2017](https://www.unb.ca/cic/datasets/ids-2017.html)).

**ML for IDS.** Tree ensembles and gradient boosting are widely used on flow features because they handle mixed-scale tabular inputs and class imbalance reasonably well when paired with appropriate metrics (precision/recall/F1 rather than accuracy alone).

**Explainability.** Lundberg & Lee’s **SHAP** and Ribeiro et al.’s **LIME** are standard local explanation methods. In security settings they help analysts inspect *why* a flow was flagged, improving trust without proving causality (SHAP as additive feature attribution; LIME as a local linear surrogate).

**Decision support / SOAR.** Security orchestration platforms map alerts to playbooks. This project adopts that idea at student scale: attack family → **advisory** recommendation, with no automatic destructive network changes.

**Positioning.** Prior work often isolates either “high accuracy on CICIDS” or “dashboard demo.” Aegis IDS integrates detection, multiclass labelling, risk scoring, SHAP/LIME, recommendations, and attack–defense simulation in one reproducible platform.

### References (starter set)

1. I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, “Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization,” in *ICISSP*, 2018, pp. 108–116. DOI: [10.5220/0006639801080116](https://doi.org/10.5220/0006639801080116).
2. Canadian Institute for Cybersecurity, “Intrusion Detection Evaluation Dataset (CIC-IDS2017),” University of New Brunswick. https://www.unb.ca/cic/datasets/ids-2017.html
3. S. M. Lundberg and S.-I. Lee, “A Unified Approach to Interpreting Model Predictions,” in *NeurIPS*, 2017.
4. M. T. Ribeiro, S. Singh, and C. Guestrin, “‘Why Should I Trust You?’ Explaining the Predictions of Any Classifier,” in *KDD*, 2016.
5. T. Chen and C. Guestrin, “XGBoost: A Scalable Tree Boosting System,” in *KDD*, 2016.
6. R. Sommer and V. Paxson, “Outside the Closed World: On Using Machine Learning for Network Intrusion Detection,” in *IEEE S&P*, 2010.
7. A. L. Buczak and E. Guven, “A Survey of Data Mining and Machine Learning Methods for Cyber Security Intrusion Detection,” *IEEE Communications Surveys & Tutorials*, 2016.
8. H.-J. Liao et al., “Intrusion Detection System: A Comprehensive Review,” *Journal of Network and Computer Applications*, 2013.
9. D. Gunning and D. Aha, “DARPA’s Explainable Artificial Intelligence (XAI) Program,” *AI Magazine*, 2019.
10. N. Moustafa and J. Slay, “UNSW-NB15: A Comprehensive Data Set for Network Intrusion Detection Systems,” in *MilCIS*, 2015.

*(Add institution-specific formatting / more recent XAI-for-IDS papers as required by your guide.)*

---

## 5. System architecture

Layers: UI (React) → API (FastAPI) → ML engine + Security engine + Simulation engine → Data (CICIDS, models, SQLite incidents).

Two-stage ML:

1. **Binary:** BENIGN vs ATTACK — frozen model **Decision Tree**, threshold **0.85**
2. **Multiclass (attack-only):** Bot, BruteForce, DDoS, DoS, PortScan, WebAttack — frozen model **Random Forest** (no BENIGN class)

Risk score (configurable weights in `config.yaml`):

```text
0.50·attack_base + 0.25·confidence·100 + 0.15·intensity·100 + 0.10·asset_criticality (scaled)
```

Recommendations are **advisory only**. Simulation is **visualization only** (no real attacks). Defense effectiveness percentages are **assumptions**, not measured mitigation rates.

---

## 6. Dataset & preprocessing

- Source: CICIDS2017 MachineLearningCVE CSVs (~2.83M raw rows)  
- Cleaning: strip columns, drop leakage fields, coerce numeric, remove Inf/NaN/duplicates  
- Label families normalized (e.g., DoS Hulk → DoS)  
- Rare classes with &lt; 50 samples dropped (Infiltration, Heartbleed) → **2,520,751** flows  
- Stratified split: train 70% / val 10% / test 20%  
- Features: StandardScaler + SelectKBest(**f_classif**, k=40) fit **on train only** (dual selectors)

See `data/processed/summary.json` and `models/trained_models/model_metadata.json`.

---

## 7. Experimental results (RQ1)

### Binary (validation)

| Model | Precision | Recall | F1 | ROC-AUC | Selection score |
|-------|----------:|-------:|---:|--------:|----------------:|
| logistic_regression | 0.7206 | 0.9706 | 0.8272 | 0.9860 | 0.9239 |
| **decision_tree** | **0.9845** | **0.9966** | **0.9905** | **0.9989** | **0.9940** |
| random_forest | 0.9863 | 0.9961 | 0.9912 | 0.9999 | 0.9877 |
| xgboost | 0.9961 | 0.9899 | 0.9930 | 0.9999 | 0.9918 |

**Selected binary model = Decision Tree** (multi-objective: recall / F1 / PR-AUC / FPR / latency — not highest raw F1 alone).

**Test (Decision Tree, threshold 0.85):**

| Metric | Value |
|--------|------:|
| Precision | 0.98404 |
| Recall | 0.99700 |
| F1 | **0.99048** |
| PR-AUC | 0.99744 |
| ROC-AUC | **0.99916** |
| FPR | 0.00329 |
| FNR | 0.00300 |
| Brier | 0.00229 |
| ECE | 0.00242 |

### Multiclass (validation, attack-only)

| Model | macro-F1 | weighted-F1 | accuracy | Selection score |
|-------|---------:|------------:|---------:|----------------:|
| **random_forest** | **0.9983** | **0.9999** | **0.9999** | **0.9988** |
| xgboost | 0.9972 | 0.9998 | 0.9998 | 0.9980 |

**Selected multiclass model = Random Forest.**

**Test (Random Forest):**

| Metric | Value |
|--------|------:|
| Accuracy | 0.99979 |
| Macro Precision | 0.99762 |
| Macro Recall | 0.99864 |
| Macro F1 | **0.99813** |
| Weighted F1 | **0.99979** |

### Model selection rationale (algorithm comparison)

Candidates share the same preprocessing / `f_classif` k=40 pipeline — this is an **algorithm ablation**, not an architecture search.

**Binary multi-objective weights** (`config.yaml`): recall 0.30 · F1 0.25 · PR-AUC 0.20 · FPR 0.15 · latency 0.10.

| Model | Val recall | Val F1 | Val FPR | Infer(s) | selection_score |
|-------|----------:|-------:|--------:|---------:|----------------:|
| logistic_regression | 0.9706 | 0.8272 | 0.0765 | 0.015 | 0.9239 |
| **decision_tree** | **0.9966** | 0.9905 | 0.0032 | 0.030 | **0.9940** |
| random_forest | 0.9961 | 0.9912 | 0.0028 | 0.169 | 0.9877 |
| xgboost | 0.9899 | **0.9930** | **0.0008** | 0.066 | 0.9918 |

**Why Decision Tree over XGBoost?** XGBoost wins raw F1, but Decision Tree has **higher attack recall**. Under an IDS-oriented policy that prioritizes catching attacks, the selection score prefers Decision Tree. Random Forest is competitive on F1 but slower on validation inference, which the latency term penalizes.

**Multiclass:** score ≈ `0.7·macro-F1 + 0.3·weighted-F1` → Random Forest (0.9988) over XGBoost (0.9980).

Figures: `model_binary_selection_scores.png`, `model_binary_f1_vs_recall.png`, `model_binary_metric_bars.png`, `model_multiclass_selection.png`, `model_selection_summary.png`  
Details: `docs/experiments/MODEL_COMPARISON.md`

### Why these numbers are not deployment guarantees

CICIDS2017 is a labelled **benchmark**. IID stratified splits overstate similarity to future live traffic. Temporal holdout and drift analyses in-repo explore generalization limits; treat high F1 as evidence of strong in-dataset discrimination, not as a promise of production IDS performance.

### Figures to insert

- `models/trained_models/figures/binary_confusion_matrix.png`  
- `models/trained_models/figures/binary_roc.png`  
- `models/trained_models/figures/multiclass_confusion_matrix.png`  
- `models/trained_models/figures/feature_importance.png`

**Discussion:** Accuracy alone is insufficient under imbalance (~83% benign). High attack recall is prioritized for IDS usefulness. Stage-2 multiclass excludes BENIGN so family probabilities are conditioned on the attack branch.

---

## 8. Temporal generalization evaluation

Artifact: `models/trained_models/temporal_holdout_report.json`  
Script: `scripts/25_temporal_holdout_eval.py` (score) · `scripts/28_plot_temporal_generalization.py` (figures)  
Figures: `models/trained_models/figures/temporal_*.png`

### Experimental setup

| Item | Definition |
|------|------------|
| Models | Frozen **Decision Tree** (`binary_best.joblib`) @ threshold **0.85**; frozen **Random Forest** (`multiclass_best.joblib`); shared `feature_bundle.joblib` |
| Retrain? | **No** — day slices score the freeze artifacts only |
| Day definition | CICIDS2017 MachineLearningCVE day-named CSVs (`Monday`…`Friday`) |
| Sampling | Cap **12,000** rows per CSV (`research.temporal_sample_per_file` / freeze default) |
| Friday temporal | **36,000** flows (attack rate ≈ **33.8%**) |
| Mon–Thu reference | **60,000** flows (attack rate ≈ **6.9%**) |
| IID reference | Full stratified test metrics from `training_report.json` (not re-sampled here) |

### Why temporal holdout matters

A stratified IID split mixes days (and scenarios) into train/val/test. That can overstate how a model behaves when the **next day’s attack mix** differs. A day-aware Friday holdout is a modest, honest check of **within-CICIDS temporal / scenario shift** — not a live network trial.

### Binary: IID vs temporal

| Split | n | Attack rate | Precision | Recall | F1 | ROC-AUC |
|-------|--:|------------:|----------:|-------:|---:|--------:|
| IID stratified test | 504,151 | ~16.9% | 0.98404 | 0.99700 | **0.99048** | 0.99916 |
| Friday temporal sample | 36,000 | 33.8% | 0.99901 | 0.99638 | **0.99770** | 0.99983 |
| Mon–Thu sample | 60,000 | 6.9% | 0.98631 | 0.97370 | **0.97997** | 0.99894 |

**Degradation / change (IID − slice):**

| Contrast | Δ F1 | Δ Recall | Notes |
|----------|-----:|---------:|-------|
| IID − Friday | **−0.00722** | +0.00062 | Friday F1 is *higher*; prevalence and attack mix differ |
| IID − Mon–Thu | **+0.01051** | +0.02330 | Mild F1/recall drop on low-prevalence early-week sample |

Insert: `temporal_binary_iid_vs_holdout.png`, `temporal_generalization_summary.png`.

### Multiclass: IID vs temporal

| Evaluation | Scope | Accuracy | Macro-F1 | Weighted-F1 |
|------------|-------|---------:|---------:|------------:|
| IID stratified test | **6** attack classes | 0.99979 | 0.99813 | 0.99979 |
| Friday temporal sample | **3** present classes only | 1.00000 | 1.00000 | 1.00000 |

Friday families **present:** Bot, DDoS, PortScan (supports 108 / 6915 / 5142).  
Friday families **absent** from the scored attack subset: BruteForce, DoS, WebAttack.

Mon–Thu multiclass scoring was **skipped** in the freeze run because raw day samples contained labels outside the freeze class set (e.g. `Infiltration`).

Insert: `temporal_multiclass_iid_vs_holdout.png`, `temporal_friday_multiclass_confusion.png`, `temporal_friday_classwise.png`.

### Interpretation

1. **Binary detection remains strong** under the Friday day sample; headline F1 does not collapse relative to IID.  
2. **Composition matters:** attack rates of 6.9% vs 33.8% change precision/recall trade-offs; do not interpret a higher Friday F1 as “better than IID” without discussing prevalence.  
3. **Mon–Thu** shows a modest binary F1 drop (~1.05 pp) and larger recall drop (~2.3 pp) — useful evidence that day/scenario slices are not identical to the IID test.  
4. **Friday multiclass “perfect” scores are not a six-class temporal claim** — only three families appeared in that sample after attack-only encoding.

### Limitations & threats to validity

- Day slices are **capped samples**, not exhaustive day populations.  
- CICIDS2017 days are **scenario-structured**, not continuous live enterprise traffic.  
- Multiclass temporal coverage is **incomplete** (subset of families; rare-label skip on Mon–Thu).  
- No claim of production IDS readiness or absence of concept drift in the wild.

### What this does — and does not — claim

**Does claim:** Within this freeze, scoring the Decision Tree / Random Forest artifacts on day-aware CICIDS samples yields competitive binary metrics and a documented, limited multiclass temporal slice — supporting discussion of generalization **beyond the IID split**.

**Does not claim:** Live-network performance, cross-organization transfer, or measured real-world mitigation.

**External-dataset validation** was not performed within the current experimental scope and is identified as **future work** for assessing cross-dataset generalization.

---

## 9. IID data-drift monitoring

Artifact: `models/trained_models/drift_report.json`  
Scripts: `scripts/20_data_drift_report.py`, `scripts/29_plot_drift_and_errors.py`  
Figures: `drift_psi_train_vs_test.png`, `drift_label_distribution.png`

### Setup

| Item | Value |
|------|--------|
| Reference | Processed **train** (n = 1,764,525) |
| Current | Processed **test** (n = 504,151) |
| Scope | Stratified **IID** splits from the same CICIDS2017 corpus |
| Features compared | 78 |

### Results (freeze)

| Check | Result |
|-------|--------|
| Features with PSI ≥ 0.2 | **None** |
| Max listed PSI | **0.0** |
| Label distribution Δ (percentage points) | **≈ 0** for all labels |
| Retrain recommendation | `monitor` (`promote: false`) |

### Interpretation

Near-zero PSI under train→test is **expected** when both splits are stratified draws from one cleaned corpus. It is a useful integrity / monitoring check, not evidence that live traffic or another day’s scenario mix will look identical.

### What this does — and does not — claim

**Does claim:** Within the freeze, the IID train/test feature and label distributions show no high-PSI flags.  
**Does not claim:** Absence of temporal, operational, or cross-dataset drift (see §8 and future work).

---

## 10. Error analysis (residual confusions)

Artifact: `models/trained_models/error_analysis_report.json`  
Scripts: `scripts/23_error_analysis.py`, `scripts/29_plot_drift_and_errors.py`  
Figures: `error_binary_fp_fn_counts.png`, `error_multiclass_top_confusions.png`  
Also: IID CMs from `scripts/05_plot_evaluation.py`

### Binary residuals (Decision Tree, IID test)

| | Count |
|--|------:|
| True negatives | 417,635 |
| False positives | **1,377** |
| False negatives | **255** |
| True positives | 84,884 |

FPR = 0.00329 · FNR = 0.00300 · F1 = 0.99048

### Multiclass residuals (Random Forest, attack-only IID test)

**18** misclassifications among **85,139** attack flows. Top off-diagonal pairs:

| True → Pred | Count |
|-------------|------:|
| PortScan → DoS | 6 |
| PortScan → WebAttack | 3 |
| DoS → WebAttack | 3 |
| DoS → PortScan | 2 |
| WebAttack → DoS | 2 |
| WebAttack → PortScan | 1 |
| BruteForce → DoS | 1 |

Bot and DDoS show perfect diagonals on this test CM. Residual difficulty concentrates in the **PortScan / DoS / WebAttack** neighborhood — plausible given overlapping volumetric / probing behaviors in flow space.

### What this does — and does not — claim

**Does claim:** Residual error mass is small on the IID test set and structurally concentrated among a few family pairs.  
**Does not claim:** Acceptable false-alarm rates under live SOC traffic, or that rare families are equally easy.

---

## 11. Feature importance & XAI (RQ2, RQ3)

- Global importance: tree importances (figure above)  
- Local explanation (primary): **SHAP** via `POST /api/explain` `method=shap`  
- Local explanation (secondary): **LIME** via `method=lime`  

SHAP answers “which features pushed this flow toward the predicted class?”  
LIME fits a local linear surrogate for complementary intuition. Neither proves causality; both support analyst trust.

---

## 12. Risk & recommendations (RQ4)

Attack family + confidence + optional intensity + asset criticality → risk score → severity band (LOW/MEDIUM/HIGH/CRITICAL).  
Weights: **50% / 25% / 15% / 10%** as in §5.  
Recommendation engine maps families to defensive playbooks (rate limiting, WAF, isolation, etc.) with explicit **advisory** disclaimer.

---

## 13. Simulation (RQ5)

State machine: `idle → normal → attack_start → attack_impact → detected → recommended → defended → recovered`  
Rendered with React Flow. Evaluated qualitatively by whether each scenario reaches mitigation and communicates the lifecycle clearly.  
**Simulation defense effectiveness ≠ empirically measured real-world mitigation.**

---

## 14. Implementation

| Module | Path |
|--------|------|
| Data prep | `ml/preprocessing/`, `scripts/01_prepare_data.py` |
| Training | `scripts/02_train_models.py` |
| Predict | `ml/prediction/predictor.py` |
| SHAP / LIME | `explainability/` |
| Risk / Recs | `security/` |
| Simulation | `simulation/engine/core.py` |
| Temporal eval | `scripts/25_temporal_holdout_eval.py`, `scripts/28_plot_temporal_generalization.py` |
| Drift / errors | `scripts/20_data_drift_report.py`, `scripts/23_error_analysis.py`, `scripts/29_plot_drift_and_errors.py` |
| Model comparison | `scripts/04_export_comparison.py`, `scripts/30_plot_model_comparison.py` |
| API | `backend/` |
| UI | `frontend/` |

Reproduce:

```bash
python scripts/01_prepare_data.py
python scripts/02_train_models.py
python scripts/05_plot_evaluation.py
python scripts/20_data_drift_report.py
python scripts/23_error_analysis.py
python scripts/25_temporal_holdout_eval.py   # needs MachineLearningCVE CSVs
python scripts/28_plot_temporal_generalization.py
python scripts/29_plot_drift_and_errors.py
uvicorn backend.main:app --port 8000
cd frontend && npm run dev
```

Or `docker compose up --build` after artifacts exist.

---

## 15. Limitations & future work

- CICIDS2017 is dated relative to modern traffic; concept drift possible  
- Simulation is pedagogical visualization, not a network emulator or live IDS  
- Recommendations are rule/playbook-mapped decision support, not learned policies or auto-mitigation  
- Calibration remains **disabled** after research trade-off (ECE vs recall/Brier); see `docs/experiments/CALIBRATION_AND_THRESHOLD.md`  
- Temporal holdout is day-sample based within CICIDS2017 — see §8 threats to validity  
- IID drift PSI≈0 does **not** imply live or cross-dataset stability — see §9  
- **External-dataset validation was not performed within the current experimental scope and is identified as future work for assessing cross-dataset generalization.**  
- Live PCAP/flow ingestion and production IAM are Stage-2 / future engineering tracks  

See also `docs/IMPLEMENTATION_STATUS.md` and `docs/STAGE2_PRODUCTION.md`.

---

## 16. Conclusion

Aegis IDS demonstrates that an ML IDS becomes far more useful when coupled with explainability, risk scoring, defensive recommendations, and interactive simulation. The frozen Decision Tree + Random Forest pipeline answers not only *whether* traffic is malicious, but *what*, *why*, *how severe*, and *what an analyst might do next* — within an honest research/prototype framing that separates **IID benchmark strength**, **temporal caution**, and **residual error structure** from production-deployment claims.

---

## Appendix A — One-sentence project definition

> We are building an intelligent machine-learning-based intrusion detection platform that detects and classifies network attacks, explains the reasons behind its predictions, assesses their risk, recommends appropriate defensive actions, and interactively simulates the attack-to-defense lifecycle through a visual network environment.

## Appendix B — Ethics & safety

No real attacks are launched. Defenses are not auto-executed against production networks.
