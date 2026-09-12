# Implementation status (honest inventory)

Last updated with the Batch-1/Batch-3 hardening pass.

## Implemented

- CICIDS2017 load/clean/split + rare-class filter (documented)
- Two-stage ML (binary + multiclass) with trained artifacts
- Feature validation on predict (422 if schema incomplete; demo can opt-in to fill)
- Explicit binary class-index via `model.classes_`
- Certainty bands (likely_benign / uncertain / likely_attack)
- SHAP with `actual_method` / `fallback_used` (no silent “fake SHAP”)
- LIME as secondary explainer
- Risk + advisory recommendations
- Attack-specific simulation topologies/behaviors (DDoS, DoS, PortScan, BruteForce, WebAttack, Bot)
- Simulation narrative + simulated metrics
- Prediction → incident → `/incidents/{id}/simulate`
- Simulation session persistence (SQLite best-effort)
- Dashboard / Detection / Simulation / Reports UI
- Docker, CI (pytest), docs, report, slides

## Partially implemented

- Simulation DB restore after restart (best-effort)
- Reports analytics (charts, not export yet)
- Incident lifecycle (status field exists; limited transitions)
- Rule engine directory (`security/rules`) still thin

## Not implemented (do not claim)

- Live packet capture / real-time network IDS
- Automatic network mitigation
- WebSockets / true live SOC streaming
- Cross-dataset evaluation (CSE-CIC-IDS2018)
- Hyperparameter search / calibration curves (planned research)
- Separate binary vs multiclass feature selectors (planned experiment)

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
