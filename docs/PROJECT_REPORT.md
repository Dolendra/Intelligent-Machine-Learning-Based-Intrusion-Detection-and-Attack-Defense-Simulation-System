# Intelligent ML-Based Intrusion Detection and Attack–Defense Simulation System

**Platform name:** Aegis IDS  
**Dataset:** CICIDS2017 (`MachineLearningCVE`)  
**Stack:** Python · Scikit-learn / XGBoost (compared) · SHAP / LIME · FastAPI · React · SQLite  
**Frozen models (v1.1):** Binary **Decision Tree** @ threshold **0.85** · Multiclass **Random Forest** (attack-only)

> Use this document as the backbone of your major-project report. Copy sections into Word/LaTeX and insert figures from `models/trained_models/figures/`. Authoritative metrics: `models/trained_models/model_metadata.json` and `training_report.json`.

---

## 1. Abstract

This project presents an integrated intelligent intrusion detection platform that goes beyond raw classifier accuracy. The system detects malicious network flows, classifies attack families, estimates risk, explains predictions with SHAP (primary) and LIME (secondary), recommends advisory defensive actions, and interactively simulates the attack-to-defense lifecycle on a simplified enterprise topology. On CICIDS2017, the frozen binary Decision Tree achieves test F1 **0.99048** and ROC-AUC **0.99916** (threshold 0.85); the frozen attack-only Random Forest multiclass model achieves macro-F1 **0.99813** and weighted-F1 **0.99979**. These benchmark results are not claims of real-world future performance under live traffic.

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

### Why these numbers are not deployment guarantees

CICIDS2017 is a labelled **benchmark**. IID stratified splits overstate similarity to future live traffic. Temporal holdout and drift analyses in-repo explore generalization limits; treat high F1 as evidence of strong in-dataset discrimination, not as a promise of production IDS performance.

### Figures to insert

- `models/trained_models/figures/binary_confusion_matrix.png`  
- `models/trained_models/figures/binary_roc.png`  
- `models/trained_models/figures/multiclass_confusion_matrix.png`  
- `models/trained_models/figures/feature_importance.png`

**Discussion:** Accuracy alone is insufficient under imbalance (~83% benign). High attack recall is prioritized for IDS usefulness. Stage-2 multiclass excludes BENIGN so family probabilities are conditioned on the attack branch.

---

## 8. Feature importance & XAI (RQ2, RQ3)

- Global importance: tree importances (figure above)  
- Local explanation (primary): **SHAP** via `POST /api/explain` `method=shap`  
- Local explanation (secondary): **LIME** via `method=lime`  

SHAP answers “which features pushed this flow toward the predicted class?”  
LIME fits a local linear surrogate for complementary intuition. Neither proves causality; both support analyst trust.

---

## 9. Risk & recommendations (RQ4)

Attack family + confidence + optional intensity + asset criticality → risk score → severity band (LOW/MEDIUM/HIGH/CRITICAL).  
Weights: **50% / 25% / 15% / 10%** as in §5.  
Recommendation engine maps families to defensive playbooks (rate limiting, WAF, isolation, etc.) with explicit **advisory** disclaimer.

---

## 10. Simulation (RQ5)

State machine: `idle → normal → attack_start → attack_impact → detected → recommended → defended → recovered`  
Rendered with React Flow. Evaluated qualitatively by whether each scenario reaches mitigation and communicates the lifecycle clearly.  
**Simulation defense effectiveness ≠ empirically measured real-world mitigation.**

---

## 11. Implementation

| Module | Path |
|--------|------|
| Data prep | `ml/preprocessing/`, `scripts/01_prepare_data.py` |
| Training | `scripts/02_train_models.py` |
| Predict | `ml/prediction/predictor.py` |
| SHAP / LIME | `explainability/` |
| Risk / Recs | `security/` |
| Simulation | `simulation/engine/core.py` |
| API | `backend/` |
| UI | `frontend/` |

Reproduce:

```bash
python scripts/01_prepare_data.py
python scripts/02_train_models.py
python scripts/05_plot_evaluation.py
uvicorn backend.main:app --port 8000
cd frontend && npm run dev
```

Or `docker compose up --build` after artifacts exist.

---

## 12. Limitations & future work

- CICIDS2017 is dated relative to modern traffic; concept drift possible  
- Simulation is pedagogical visualization, not a network emulator or live IDS  
- Recommendations are rule/playbook-mapped decision support, not learned policies or auto-mitigation  
- Calibration remains **disabled** after research trade-off (ECE vs recall/Brier); see `docs/experiments/CALIBRATION_AND_THRESHOLD.md`  
- Cross-dataset evaluation is scaffolded and requires an external compatible dataset  
- Live PCAP/flow ingestion and production IAM are Stage-2 / future engineering tracks  

See also `docs/IMPLEMENTATION_STATUS.md` and `docs/STAGE2_PRODUCTION.md`.

---

## 13. Conclusion

Aegis IDS demonstrates that an ML IDS becomes far more useful when coupled with explainability, risk scoring, defensive recommendations, and interactive simulation. The frozen Decision Tree + Random Forest pipeline answers not only *whether* traffic is malicious, but *what*, *why*, *how severe*, and *what an analyst might do next* — within an honest research/prototype framing.

---

## Appendix A — One-sentence project definition

> We are building an intelligent machine-learning-based intrusion detection platform that detects and classifies network attacks, explains the reasons behind its predictions, assesses their risk, recommends appropriate defensive actions, and interactively simulates the attack-to-defense lifecycle through a visual network environment.

## Appendix B — Ethics & safety

No real attacks are launched. Defenses are not auto-executed against production networks.
