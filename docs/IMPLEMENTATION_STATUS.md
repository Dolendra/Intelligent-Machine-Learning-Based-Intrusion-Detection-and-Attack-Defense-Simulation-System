# Implementation status (honest inventory)

Last updated with play/pause simulation, CSV batch, exports, dual feature selectors.

## Implemented

- CICIDS2017 load/clean/split + rare-class filter (documented)
- Two-stage ML (binary + multiclass) with trained artifacts
- Dual SelectKBest support (binary vs multiclass) + experiment script
- Feature validation on predict; certainty bands; class-index via `classes_`
- SHAP/LIME with honest method labeling
- Configurable risk weights + asset criticality
- Rule engine → context-aware recommendations
- Attack-specific simulation + Play/Pause/Step timeline + comparison metrics
- Prediction → incident → simulate
- Incident lifecycle transitions
- Batch prediction (JSON + CSV upload)
- Reports analytics + CSV/JSON export
- PR-AUC / FPR / FNR + error-analysis notebook
- Docker; CI (pytest + frontend build); docs

## Partially implemented

- Production artifacts may still be from shared-selector training until `02_train_models.py` is re-run
- Feature-selector experiment uses a sample (not full-dataset Optuna/calibration)
- Simulation DB restore after restart (best-effort)
- PDF report export not yet

## Not implemented (do not claim)

- Live packet capture / real-time network IDS
- Automatic network mitigation
- WebSockets / true live SOC streaming
- Cross-dataset evaluation (CSE-CIC-IDS2018)
- Full Optuna HPO / probability calibration curves
- Alembic migrations

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
