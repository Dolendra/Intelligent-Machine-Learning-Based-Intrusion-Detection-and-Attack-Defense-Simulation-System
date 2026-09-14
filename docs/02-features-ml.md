# Features & ML engine

## Feature pipeline (`ml/features/pipeline.py`)

- Fit `StandardScaler` **on train only** (no leakage)
- Dual `SelectKBest(score_func=f_classif, k=40)` selectors (binary + multiclass)
- Persist as `models/trained_models/feature_bundle.joblib`

Frozen v1.1 uses **`f_classif`**, not `mutual_info_classif`.

## Two-stage design

### Stage 1 — Binary

`BENIGN` vs `ATTACK` (`is_attack`)

Algorithms compared: Logistic Regression, Decision Tree, Random Forest, XGBoost

**Selected (frozen):** `decision_tree` @ operating threshold **0.85**  
(Multi-objective selection on validation — not raw F1 alone; see `training_report.json`.)

### Stage 2 — Multiclass (attack-only)

Attack family via label encoder. **BENIGN is not a multiclass class.**

Six attack families:

- Bot
- BruteForce
- DDoS
- DoS
- PortScan
- WebAttack

Algorithms compared: Random Forest, XGBoost (configurable)

**Selected (frozen):** `random_forest`

Best models saved as:

- `binary_best.joblib`
- `multiclass_best.joblib`

Calibration wrapper: **disabled** (`models.use_calibrated_binary: false`).

## Prediction (`ml/prediction/predictor.py`)

`IDSPredictor.predict_row(features)` returns attack flag, type, confidences, certainty band, and class probabilities.

## Metrics that matter

For IDS, **recall** and **precision** on the attack class matter more than raw accuracy under class imbalance. Authoritative numbers live in:

- `models/trained_models/training_report.json`
- `models/trained_models/model_metadata.json`
