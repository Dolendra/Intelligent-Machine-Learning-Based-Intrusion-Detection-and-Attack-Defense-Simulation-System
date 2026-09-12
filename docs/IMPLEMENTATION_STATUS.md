# Implementation status (honest inventory)

Last updated after Phase-5 Model Lab / XAI polish (global SHAP, counterfactuals, drift, experiments).

## Implemented

### Phase-1–4 (summary)
- Correctness: attack-only multiclass, SHAP shapes, severity, dedup/source_ref, thresholds, DEMO_MODE defaults
- Research scaffolding + SOC UI + simulation latencies/series/campaign sim
- Engineering: `/api/ready`, non-root Docker, request IDs, standardized errors

### Phase-5 advanced XAI / research UI
- Global + attack-specific importance (`GET /api/models/shap/global`, `scripts/24_…`)
- What-if counterfactuals (`POST /api/explain/counterfactual`) on Detection
- Model health (`GET /api/models/health`), drift (`GET /api/drift`), experiments (`GET /api/experiments`)
- Model Lab UI panels for health, global/attack drivers, drift, experiment index

## Partially implemented

- Retrain required for production artifacts to pick up attack-only multiclass encoder
- Calibration/threshold **conclusions** need values filled after experiment runs
- Drift report UI needs `scripts/20_…` artifact on disk for full display
- Attack-specific SHAP rankings richer after `scripts/24_global_shap_summary.py`
- Full browser E2E suite

## Not implemented (do not claim)

- Live packet capture / auto-mitigation / OAuth SSO

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
