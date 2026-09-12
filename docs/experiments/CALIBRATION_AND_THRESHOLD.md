# Calibration and threshold decisions (research notes)

These notes document how Aegis chooses (or declines) calibration and certainty bands.
They are **project decisions backed by experiment scripts**, not universal IDS standards.

## Threshold / uncertainty

1. Run `python scripts/15_threshold_optimization.py`
2. Artifact: `models/trained_models/threshold_operating_point.json`
3. Selection rule (current):
   - Prefer validation thresholds with **recall ≥ 0.95**
   - Among those, maximize **F1**, then prefer lower **FPR**
4. Uncertainty bands are derived from the same sweep:
   - **lower**: region where recall remains very high (≥ 0.98 when available)
   - **upper**: lowest threshold achieving high precision (≥ 0.95 when available)
5. Predictor loads this file at startup (falls back to `config.yaml` values).

**Conclusion template (fill after running the script):**

> Operating threshold = _T_. Uncertainty band = [_L_, _U_].  
> Chosen because validation F1/recall/FPR trade-off favored detection of minority attacks while bounding false alarms.

## Calibration

1. Run `python scripts/11_calibration_hpo_experiment.py` (sample-based research)
2. Optionally fit wrapper: `python scripts/14_fit_calibrated_binary.py`
3. Enable in config only if validation Brier/ECE improve **without** harming recall materially:
   - `models.use_calibrated_binary: true`

**Default:** `use_calibrated_binary: false` until evidence justifies promotion.

**Conclusion template:**

> Calibration _enabled/disabled_ because Brier/ECE changed from _X_ → _Y_ while recall stayed _R_.  
> Production still uses `binary_best.joblib` unless the calibrated artifact is explicitly promoted.

## Risk weights

See `scripts/16_risk_weight_sensitivity.py`. Weights in `config.yaml` are project conventions; report how often severity labels flip across configurations A/B/C.
