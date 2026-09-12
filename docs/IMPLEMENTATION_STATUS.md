# Implementation status (honest inventory)

Last updated after must-do research/integration pass (selection, intensity, dynamic sim, incident events/UI).

## Implemented (including recent review items)

- Dual feature selectors; prediction validation; certainty bands
- Multi-objective binary model selection weights (config-driven)
- PR-AUC/FPR/FNR/MCC/Brier/ECE; threshold sweep + risk sensitivity scripts
- Percentile-based traffic intensity (with legacy fallback)
- Rule-driven recommendations; risk with asset criticality
- Attack-specific simulation + **dynamic** metrics (detection delay, defense efficacy)
- Incident lifecycle + **event history** + Incident detail UI
- Model Lab page (comparison from training_report)
- Vectorized batch prediction; strict CSV validation
- WebSocket dashboard refresh; PDF/CSV/JSON export
- Docker healthchecks; frontend CI build; docs honesty

## Partially implemented

- Production dual-selector/calibrated artifacts need retrain / script 14
- Intensity reference requires training run (or falls back to 1e5 scale)
- Scenario modules still consolidated in `behaviors.py` (split recommended later)
- Cross-dataset scoring awaits external data

## Not implemented (do not claim)

- Live packet capture / auto-mitigation
- Full Optuna on entire CICIDS; completed CSE-CIC-2018 eval
- Auth/rate-limit production hardening; Alembic

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
