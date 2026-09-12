# Implementation status (honest inventory)

Last updated with polish pass: model metadata, optional calibration wrapper, Docker healthchecks, docs sync. App version **1.1.0**.

## Implemented

- CICIDS2017 pipeline, two-stage ML, dual feature-selector support
- Prediction validation, certainty bands, SHAP/LIME honesty
- Risk + rule-driven recommendations + incident lifecycle
- Attack-specific simulation with Play/Pause/Step + comparison metrics
- Batch JSON/CSV prediction; Reports CSV/JSON/PDF export
- Dashboard auto-refresh (WebSocket + polling fallback)
- Calibration metrics (Brier/ECE) + sample HPO / calibration scripts
- Cross-dataset status scaffold
- `model_metadata.json` reproducibility writer (`scripts/13_write_model_metadata.py`)
- Optional calibrated binary wrapper (`scripts/14_fit_calibrated_binary.py`)
- Docker healthchecks; frontend `npm ci`
- CI (pytest + frontend build); notebooks 01–07

## Partially implemented

- Production dual-selector / calibrated models require retrain or script 14 + config flag
- HPO/calibration experiments are sample-based (not full Optuna on entire CICIDS)
- Cross-dataset scoring awaits external dataset on disk
- WebSocket refreshes analytics — not packet-level live IDS

## Not implemented (do not claim)

- Live packet capture / automatic network mitigation
- Completed CSE-CIC-IDS2018 evaluation without that dataset
- Alembic migrations / multi-tenant production SOC

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
