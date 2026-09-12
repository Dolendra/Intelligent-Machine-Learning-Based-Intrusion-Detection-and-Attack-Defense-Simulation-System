# Implementation status (honest inventory)

Last updated with calibration/HPO research, WebSocket dashboard refresh, PDF export.

## Implemented

- CICIDS2017 pipeline, two-stage ML, dual feature-selector support
- Prediction validation, certainty bands, SHAP/LIME honesty
- Risk + rule-driven recommendations + incident lifecycle
- Attack-specific simulation with Play/Pause/Step
- Batch JSON/CSV prediction; Reports CSV/JSON/**PDF** export
- Dashboard auto-refresh via **WebSocket** (polling fallback)
- Calibration metrics (Brier, ECE) + sample HPO experiment script
- Cross-dataset status scaffold script
- Docker; CI; notebooks including calibration analysis

## Partially implemented

- Production models may predate dual selectors / calibrated wrappers until retrain
- HPO/calibration experiments are **sample-based**, not full-dataset Optuna
- Cross-dataset evaluation awaits CSE-CIC-IDS2018 (or compatible) data on disk
- WebSocket pushes analytics snapshots (not packet-level live IDS)

## Not implemented (do not claim)

- Live packet capture / automatic network mitigation
- Full Optuna multi-objective search on entire CICIDS2017
- Completed cross-dataset scoring without external data
- Alembic migrations

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
