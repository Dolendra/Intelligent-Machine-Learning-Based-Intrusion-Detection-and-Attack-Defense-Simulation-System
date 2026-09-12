# Features & ML engine

## Feature pipeline (`ml/features/pipeline.py`)

- Fit `StandardScaler` **on train only** (no leakage)
- `SelectKBest(mutual_info_classif)` → top-K features (default 40)
- Persist as `models/trained_models/feature_bundle.joblib`

## Two-stage design

### Stage 1 — Binary

`BENIGN` vs `ATTACK` (`is_attack`)

Algorithms compared: Logistic Regression, Decision Tree, Random Forest, XGBoost

### Stage 2 — Multiclass

Attack family via `Label` (including BENIGN for label consistency)

Algorithms: Random Forest, XGBoost (configurable)

Best models saved as:

- `binary_best.joblib`
- `multiclass_best.joblib`

## Prediction (`ml/prediction/predictor.py`)

`IDSPredictor.predict_row(features)` returns attack flag, type, confidences, and class probabilities.

## Metrics that matter

For IDS, **recall** and **precision** on the attack class matter more than raw accuracy under class imbalance. Reports land in `models/trained_models/training_report.json`.
