# Implementation status (honest inventory)

Last updated after Phase-2 research docs + Phase-3 SOC UI (risk why, campaigns, analyst notes, report filters).

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
- Label / rare-class audit script (`scripts/21_…`)
- Experiment index writer (`scripts/22_…`)
- Calibration/threshold decision notes (`docs/experiments/CALIBRATION_AND_THRESHOLD.md`) — fill conclusions after running sweeps
- Enhanced model metadata (git commit, config hash, split sizes, uncertainty, attack classes)

### Phase-3 SOC UI
- Risk contributions + “Why this risk?” on Detection
- Campaigns list/detail pages (`/campaigns`, `/campaigns/:id`) + API `GET /api/campaigns`
- Analyst notes + defense action on Incident Detail
- Dashboard: clickable incident IDs, risk distribution bars, View all
- Reports: severity / attack / status / campaign filters

## Partially implemented

- Retrain required for production artifacts to pick up attack-only multiclass encoder
- Calibration/threshold **conclusions** need values filled after experiment runs
- External CSE-CIC-IDS2018 needs compatible CSVs on disk
- Intensity reference / calibrated binary need training/script runs

## Not implemented (do not claim)

- Live packet capture / auto-mitigation / OAuth SSO
- Full golden-path E2E browser suite
- Non-root Docker / `/api/ready` hardening polish

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
