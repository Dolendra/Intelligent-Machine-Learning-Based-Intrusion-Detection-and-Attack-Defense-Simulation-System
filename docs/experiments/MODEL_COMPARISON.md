# Model comparison & selection

Scripts: `scripts/04_export_comparison.py`, `scripts/30_plot_model_comparison.py`
Source: `models/trained_models/training_report.json`
Figures: `model_binary_*.png`, `model_multiclass_selection.png`, `model_selection_summary.png`

## Binary selection policy

Multi-objective score (project-justified weights in `config.yaml`):

- recall **0.30**
- F1 **0.25**
- PR-AUC **0.20**
- FPR penalty **0.15**
- latency **0.10**

**Selected:** `decision_tree`

| Model | Recall | F1 | PR-AUC | FPR | Infer(s) | selection_score |
|-------|-------:|---:|-------:|----:|---------:|----------------:|
| logistic_regression | 0.9706 | 0.8272 | 0.9405 | 0.0765 | 0.015 | 0.923853 |
|  **decision_tree** | 0.9966 | 0.9905 | 0.9972 | 0.0032 | 0.0303 | 0.994048 |
| random_forest | 0.9961 | 0.9912 | 0.9997 | 0.0028 | 0.1689 | 0.987715 |
| xgboost | 0.9899 | 0.9930 | 0.9997 | 0.0008 | 0.0657 | 0.991752 |

### Why not XGBoost?

XGBoost has the highest validation F1, but **lower recall** than Decision Tree. Under an IDS-oriented policy that weights recall first, Decision Tree wins the selection score.

## Multiclass selection

Score ≈ `0.7·macro-F1 + 0.3·weighted-F1` on attack-only classes.

**Selected:** `random_forest`

| Model | macro-F1 | weighted-F1 | selection_score |
|-------|---------:|------------:|----------------:|
| **random_forest** | 0.9983 | 0.9999 | 0.998767 |
| xgboost | 0.9972 | 0.9998 | 0.998016 |

## Claims

- Comparison is an **algorithm ablation under a fixed feature pipeline**, not an architecture search.
- Selection is policy-dependent; different weights could prefer XGBoost.
- Final test metrics for selected models are reported in `PROJECT_REPORT.md` §7.
