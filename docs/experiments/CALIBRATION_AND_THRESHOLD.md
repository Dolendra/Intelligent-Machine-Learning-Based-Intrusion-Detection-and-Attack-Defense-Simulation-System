# Calibration and threshold decisions (research notes)

These notes document how Aegis chooses (or declines) calibration and certainty bands.
They are **project decisions backed by experiment scripts**, not universal IDS standards.

Artifacts:
- `models/trained_models/threshold_operating_point.json`
- `models/trained_models/threshold_sweep.json`
- `models/trained_models/calibration_hpo_experiment.json`

## Threshold / uncertainty

1. Run `python scripts/15_threshold_optimization.py`
2. Selection rule:
   - Prefer validation thresholds with **recall ≥ 0.95**
   - Among those, maximize **F1**, then prefer lower **FPR**
3. Uncertainty bands from the same sweep:
   - **lower**: region where recall remains very high (≥ 0.98 when available)
   - **upper**: lowest threshold achieving high precision (≥ 0.95 when available)
4. Predictor loads `threshold_operating_point.json` at startup (config.yaml is fallback only).

### Conclusion (filled from val sweep, 150k rows)

> **Operating threshold = 0.30.** Uncertainty band = **[0.10, 0.45]**.  
> Chosen because among thresholds with recall ≥ 0.95, **T=0.30** maximized F1 (**0.9935**) with recall **0.9947**.  
> Band derivation: lower≈threshold where recall stays ≥0.98 (0.10); upper≈lowest threshold with precision ≥0.95 (0.45).

`config.yaml` mirrors these values for documentation; runtime prefers the JSON artifact.

## Calibration

1. Run `python scripts/11_calibration_hpo_experiment.py` (sample-based research RF baseline)
2. Optionally fit wrapper: `python scripts/14_fit_calibrated_binary.py`
3. Enable only if Brier/ECE improve **without** harming recall materially:
   - `models.use_calibrated_binary: true`

### Conclusion (filled from sample experiment)

| Variant | Recall | F1 | Brier | ECE |
|--------|--------|-----|-------|-----|
| Baseline RF | 0.9860 | 0.9900 | 0.00283 | 0.00146 |
| Isotonic calibrated | 0.9819 | 0.9877 | 0.00367 | 0.00139 |

> **Calibration disabled** (`use_calibrated_binary: false`).  
> Isotonic calibration slightly improved ECE (0.00146 → 0.00139) but **worsened Brier** (0.00283 → 0.00367) and reduced recall.  
> Production continues to use `binary_best.joblib` (XGBoost from full training) unless a future calibrated artifact clearly wins on Brier+ECE without recall loss.

## Risk weights

See `scripts/16_risk_weight_sensitivity.py` → `risk_weight_sensitivity.json`.

### Conclusion

Across configs A (severity-heavy), B (balanced / default), and C (ops-heavy):

- DDoS high-intensity stays **CRITICAL** in all configs (~92–93).
- PortScan medium stays **MEDIUM** (~54–55).
- Severity **labels did not flip** across A/B/C for the probed cases; scores moved by ≤ ~7 points (web_low_asset: 73.8 → 67.2 under ops-heavy).
- Default balanced weights in `config.yaml` are retained as the project convention.

## Drift (train vs test)

`scripts/20_data_drift_report.py` → `drift_report.json`:

> **0 features** with PSI ≥ 0.2 on the in-project train→test split (78 features compared). Recommendation: **monitor** (no retrain trigger from IID holdout drift alone).
