# Implementation status (honest inventory)

Last updated after Phase-4 simulation excellence + Phase-6 engineering hardening.

## Implemented

### Phase-1 correctness
- Stage-2 multiclass trained on **attack rows only** with `attack_label_encoder` (BENIGN excluded)
- SHAP class extraction handles `(samples, features, classes)` and `(classes, samples, features)` with feature-count checks
- Incident dedup/campaign require **explicit** `source_ref` (no Destination Port fingerprint)
- Risk severity uses lower-bound cuts (fractional 30.5/60.5/80.5 handled correctly)
- Uncertainty bands derived by `scripts/15_threshold_optimization.py` → `threshold_operating_point.json`
- Intensity reports `percentile_reference` vs `legacy_scale`
- Cross-dataset official metrics only when feature overlap is **100%**
- `DEMO_MODE` defaults to **false**; `/api/predict` ignores `allow_missing_features` unless DEMO_MODE

### Phase-2 research scaffolding
- Label / rare-class audit, experiment index, enhanced metadata
- Calibration/threshold decision notes (`docs/experiments/…`) — fill conclusions after running sweeps
- Error analysis script (`scripts/23_error_analysis.py`)

### Phase-3 SOC UI
- Risk why, campaigns pages, analyst notes, report filters, dashboard links/risk bars

### Phase-4 simulation excellence
- Real ISO timestamps + elapsed `t_s` on timeline events
- Detection / defense / recovery latencies derived from session wall-clock
- Before/after series + no-defense counterfactual charts in Simulation UI
- Campaign simulation (`POST /api/campaigns/{id}/simulate`)
- Mild intensity-based topology labeling

### Phase-6 engineering
- `GET /api/ready` (503 until models load)
- Non-root API Docker user (`aegis` uid 10001)
- Request IDs (`X-Request-ID`) on responses + structured logs
- Standardized error envelopes (`code` / `message` / `request_id`)
- Clearer Alembic fallback logging; lifespan fails loudly on DB init errors

## Partially implemented

- Retrain required for production artifacts to pick up attack-only multiclass encoder
- Calibration/threshold **conclusions** need values filled after experiment runs
- External CSE-CIC-IDS2018 needs compatible CSVs on disk
- Global/attack-specific SHAP dashboards, drift UI, full browser E2E suite

## Not implemented (do not claim)

- Live packet capture / auto-mitigation / OAuth SSO

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
