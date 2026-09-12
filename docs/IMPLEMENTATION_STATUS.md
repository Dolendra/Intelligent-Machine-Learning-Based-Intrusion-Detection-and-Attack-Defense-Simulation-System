# Implementation status (honest inventory)

Last updated with the Phase-2/3 hardening pass (rules, risk context, lifecycle, batch).

## Implemented

- CICIDS2017 load/clean/split + rare-class filter (documented)
- Two-stage ML (binary + multiclass) with trained artifacts
- Feature validation on predict (422 if schema incomplete; demo can opt-in to fill)
- Explicit binary class-index via `model.classes_`
- Certainty bands (likely_benign / uncertain / likely_attack)
- SHAP with `actual_method` / `fallback_used` (no silent “fake SHAP”)
- LIME as secondary explainer
- Configurable risk weights + asset criticality factor
- Rule engine (`security/rules`) driving context-aware recommendations
- Attack-specific simulation topologies/behaviors
- Prediction → incident → simulate; session query handoff
- Incident lifecycle transitions (`PATCH /api/incidents/{id}`)
- Batch prediction (`POST /api/predict/batch`) + Detection batch demo
- PR-AUC / FPR / FNR in metrics + training console/report metadata
- Error-analysis notebook (`notebooks/06_error_analysis.ipynb`)
- Dashboard / Detection / Simulation / Reports UI
- Docker; CI (pytest + frontend build/tsc); docs

## Partially implemented

- Simulation DB restore after restart (best-effort)
- Reports export (PDF/CSV) not yet
- Hyperparameter search / calibration curves (research next)
- Separate binary vs multiclass feature selectors (planned experiment)
- Play/pause auto-timeline for simulation

## Not implemented (do not claim)

- Live packet capture / real-time network IDS
- Automatic network mitigation
- WebSockets / true live SOC streaming
- Cross-dataset evaluation (CSE-CIC-IDS2018)
- Alembic migrations (SQLite lightweight alters only)

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
