# Model comparison (from training_report.json)

**Frozen selection (v1.1):** binary = `decision_tree` · multiclass = `random_forest`
Binary selection is **multi-objective** (recall / F1 / PR-AUC / FPR / latency).

## Binary validation

| Model | Precision | Recall | F1 | ROC-AUC | selection_score |
|-------|----------:|-------:|---:|--------:|----------------:|
| logistic_regression | 0.7206 | 0.9706 | 0.8272 | 0.9860 | 0.923853 |
| **decision_tree** | 0.9845 | 0.9966 | 0.9905 | 0.9989 | 0.994048 |
| random_forest | 0.9863 | 0.9961 | 0.9912 | 0.9999 | 0.987715 |
| xgboost | 0.9961 | 0.9899 | 0.9930 | 0.9999 | 0.991752 |

**Best binary:** `decision_tree`
**Test:** precision=0.98404, recall=0.99700, F1=0.99048, ROC-AUC=0.99916, PR-AUC=0.99744

## Multiclass validation (attack-only)

| Model | macro-F1 | weighted-F1 | accuracy | selection_score |
|-------|---------:|------------:|---------:|----------------:|
| **random_forest** | 0.9983 | 0.9999 | 0.9999 | 0.998767 |
| xgboost | 0.9972 | 0.9998 | 0.9998 | 0.998016 |

**Best multiclass:** `random_forest`
**Test:** accuracy=0.99979, macro-F1=0.99813, weighted-F1=0.99979
