# Implementation status (honest inventory)

Last updated after Phase-1 correctness pass (attack-only multiclass, SHAP shapes, severity, dedup, thresholds).

## Implemented

- Stage-2 multiclass trained on **attack rows only** with `attack_label_encoder` (BENIGN excluded)
- SHAP class extraction handles `(samples, features, classes)` and `(classes, samples, features)` with feature-count checks
- Incident dedup/campaign require **explicit** `source_ref` (no Destination Port fingerprint)
- Risk severity uses lower-bound cuts (fractional 30.5/60.5/80.5 handled correctly)
- Uncertainty bands derived by `scripts/15_threshold_optimization.py` → `threshold_operating_point.json`
- Intensity reports `percentile_reference` vs `legacy_scale`
- Cross-dataset official metrics only when feature overlap is **100%**
- `DEMO_MODE` defaults to **false**; `/api/predict` ignores `allow_missing_features` unless DEMO_MODE
- Full Aegis loop + research scripts + SOC/sim UI as previously documented

## Partially implemented

- Retrain required for production artifacts to pick up attack-only multiclass encoder
- External CSE-CIC-IDS2018 needs compatible CSVs on disk
- Intensity reference / calibrated binary need training/script runs

## Not implemented (do not claim)

- Live packet capture / auto-mitigation / OAuth SSO

## Academic wording

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
