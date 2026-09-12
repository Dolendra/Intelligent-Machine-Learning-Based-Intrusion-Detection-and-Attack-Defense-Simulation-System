# Intelligent ML-Based Intrusion Detection and Attack–Defense Simulation System

**Platform name:** Aegis IDS  
**Dataset:** CICIDS2017 (`MachineLearningCVE`)  
**Stack:** Python · Scikit-learn / XGBoost · SHAP / LIME · FastAPI · React · SQLite  

> Use this document as the backbone of your major-project report. Copy sections into Word/LaTeX and insert figures from `models/trained_models/figures/`.

---

## 1. Abstract

This project presents an integrated intelligent intrusion detection platform that goes beyond raw classifier accuracy. The system detects malicious network flows, classifies attack families, estimates risk, explains predictions with SHAP (primary) and LIME (secondary), recommends advisory defensive actions, and interactively simulates the attack-to-defense lifecycle on a simplified enterprise topology. Experiments on CICIDS2017 show strong binary detection performance (test F1 ≈ 0.993, ROC-AUC ≈ 0.9999) and high weighted multiclass F1 (≈ 0.998) after rare-class filtering.

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

*(Add 4–6 more papers from your college library for signature/anomaly IDS surveys and recent XAI-for-security work.)*

---

## 5. System architecture

Layers: UI (React) → API (FastAPI) → ML engine + Security engine + Simulation engine → Data (CICIDS, models, SQLite incidents).

Two-stage ML:

1. **Binary:** BENIGN vs ATTACK  
2. **Multiclass:** DoS, DDoS, PortScan, BruteForce, WebAttack, Bot, BENIGN  

Risk score (configurable bands):  
`0.55·attack_base + 0.30·confidence·100 + 0.15·intensity·100`

Recommendations are **advisory only**. Simulation is **visualization only** (no real attacks).

---

## 6. Dataset & preprocessing

- Source: CICIDS2017 MachineLearningCVE CSVs (~2.83M raw rows)  
- Cleaning: strip columns, drop leakage fields, coerce numeric, remove Inf/NaN/duplicates  
- Label families normalized (e.g., DoS Hulk → DoS)  
- Rare classes with &lt; 50 samples dropped (Infiltration, Heartbleed) → **2,520,751** flows  
- Stratified split: train 70% / val 10% / test 20%  
- Features: StandardScaler + SelectKBest(f_classif, k=40) fit **on train only**

See `data/processed/summary.json`.

---

## 7. Experimental results (RQ1)

### Binary (validation)

| Model | Precision | Recall | F1 | ROC-AUC |
|-------|----------:|-------:|---:|--------:|
| logistic_regression | 0.7206 | 0.9706 | 0.8272 | 0.9860 |
| decision_tree | 0.9845 | 0.9966 | 0.9905 | 0.9989 |
| random_forest | 0.9863 | 0.9961 | 0.9912 | 0.9999 |
| **xgboost** | **0.9961** | **0.9899** | **0.9930** | **0.9999** |

**Test (best = XGBoost):** precision 0.9963 · recall 0.9896 · F1 **0.9930** · ROC-AUC **0.9999**

### Multiclass (validation)

| Model | macro-F1 | weighted-F1 |
|-------|---------:|------------:|
| random_forest | 0.8063 | 0.9935 |
| **xgboost** | **0.9194** | **0.9981** |

**Test:** macro-F1 **0.9175** · weighted-F1 **0.9981**

### Figures to insert

- `models/trained_models/figures/binary_confusion_matrix.png`  
- `models/trained_models/figures/binary_roc.png`  
- `models/trained_models/figures/multiclass_confusion_matrix.png`  
- `models/trained_models/figures/feature_importance.png`

**Discussion:** Accuracy alone is insufficient under imbalance (~83% benign). High attack recall is prioritized for IDS usefulness. Macro-F1 remains lower than weighted F1 because minority classes (Bot, WebAttack) are harder; rare classes were filtered for evaluation stability.

---

## 8. Feature importance & XAI (RQ2, RQ3)

- Global importance: tree/XGB importances (figure above)  
- Local explanation (primary): **SHAP** via `POST /api/explain` `method=shap`  
- Local explanation (secondary): **LIME** via `method=lime`  

SHAP answers “which features pushed this flow toward the predicted class?”  
LIME fits a local linear surrogate for complementary intuition. Neither proves causality; both support analyst trust.

---

## 9. Risk & recommendations (RQ4)

Attack family + confidence + optional intensity → risk score → severity band (LOW/MEDIUM/HIGH/CRITICAL).  
Recommendation engine maps families to defensive playbooks (rate limiting, WAF, isolation, etc.) with explicit **advisory** disclaimer.

---

## 10. Simulation (RQ5)

State machine: `idle → normal → attack_start → attack_impact → detected → recommended → defended → recovered`  
Rendered with React Flow. Evaluated qualitatively by whether each scenario reaches mitigation and communicates the lifecycle clearly.

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
- Simulation is pedagogical, not a network emulator  
- Recommendations are rule-mapped, not learned policies  
- Future: online flow export from PCAP, PostgreSQL, analyst feedback loop, deeper class rebalancing for Bot/WebAttack  

---

## 13. Conclusion

Aegis IDS demonstrates that an ML IDS becomes far more useful when coupled with explainability, risk scoring, defensive recommendations, and interactive simulation. The system answers not only *whether* traffic is malicious, but *what*, *why*, *how severe*, and *what an analyst might do next*.

---

## Appendix A — One-sentence project definition

> We are building an intelligent machine-learning-based intrusion detection platform that detects and classifies network attacks, explains the reasons behind its predictions, assesses their risk, recommends appropriate defensive actions, and interactively simulates the attack-to-defense lifecycle through a visual network environment.

## Appendix B — Ethics & safety

No real attacks are launched. Defenses are not auto-executed against production networks.
