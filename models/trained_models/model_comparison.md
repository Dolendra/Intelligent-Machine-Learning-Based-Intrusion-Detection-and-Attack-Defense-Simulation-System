# Model comparison (from training_report.json)

**Frozen selection (v1.1):** binary = `decision_tree` · multiclass = `random_forest`  
Binary selection is **multi-objective** (recall / F1 / PR-AUC / FPR / latency) — XGBoost is compared but not selected.

## Binary validation

| Model | Precision | Recall | F1 | ROC-AUC | Selection score |
|-------|----------:|-------:|---:|--------:|----------------:|
| logistic_regression | 0.7206 | 0.9706 | 0.8272 | 0.9860 | 0.9239 |
| **decision_tree** | **0.9845** | **0.9966** | **0.9905** | **0.9989** | **0.9940** |
| random_forest | 0.9863 | 0.9961 | 0.9912 | 0.9999 | 0.9877 |
| xgboost | 0.9961 | 0.9899 | 0.9930 | 0.9999 | 0.9918 |

**Best binary:** `decision_tree`  
**Test (selected):** precision=0.98404 · recall=0.99700 · F1=0.99048 · ROC-AUC=0.99916 · PR-AUC=0.99744 · FPR=0.00329 · FNR=0.00300 · Brier=0.00229 · ECE=0.00242  
**Operating threshold:** 0.85

## Multiclass validation (attack-only; no BENIGN)

Classes: Bot, BruteForce, DDoS, DoS, PortScan, WebAttack

| Model | macro-F1 | weighted-F1 | accuracy | Selection score |
|-------|---------:|------------:|---------:|----------------:|
| **random_forest** | **0.9983** | **0.9999** | **0.9999** | **0.9988** |
| xgboost | 0.9972 | 0.9998 | 0.9998 | 0.9980 |

**Best multiclass:** `random_forest`  
**Test (selected):** accuracy=0.99979 · macro-P=0.99762 · macro-R=0.99864 · macro-F1=0.99813 · weighted-F1=0.99979
