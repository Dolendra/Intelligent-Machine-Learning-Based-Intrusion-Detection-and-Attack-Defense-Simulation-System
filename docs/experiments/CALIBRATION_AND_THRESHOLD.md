# Calibration and threshold decisions (research notes)

These notes document how Aegis chooses (or declines) calibration and certainty bands.
They are **project decisions backed by experiment scripts**, not universal IDS standards.

Artifacts:
- `models/trained_models/threshold_operating_point.json`
- `models/trained_models/threshold_sweep.json`
- `models/trained_models/calibration_hpo_experiment.json`

## Threshold / uncertainty

1. Run `python scripts/15_threshold_optimization.py` **after** each binary retrain
2. Selection rule:
   - Prefer validation thresholds with **recall ≥ 0.95**
   - Among those, maximize **F1**, then prefer lower **FPR**
3. Predictor loads `threshold_operating_point.json` at startup (config.yaml is fallback only).

### Conclusion (post Stage-2 freeze retrain)

Final binary model selected by multi-objective score: **decision_tree** (see `training_report.json`).

> **Operating threshold = 0.85.** Uncertainty band = **[0.10, 0.95]**.  
> Chosen because among thresholds with recall ≥ 0.95, **T=0.85** maximized F1 (**≈0.9940**) with recall **≈0.9924** on the validation sweep (150k rows).  
> Band derivation: lower≈threshold where recall stays ≥0.98 (0.10); upper≈lowest threshold with precision ≥0.95 (0.95).

`config.yaml`, `threshold_operating_point.json`, and `model_metadata.json` are aligned to these values.

## Calibration

### Conclusion (unchanged research decision)

| Variant | Recall | F1 | Brier | ECE |
|--------|--------|-----|-------|-----|
| Baseline RF (sample) | 0.9860 | 0.9900 | 0.00283 | 0.00146 |
| Isotonic calibrated | 0.9819 | 0.9877 | 0.00367 | 0.00139 |

> **Calibration disabled** (`use_calibrated_binary: false`).  
> Isotonic calibration slightly improved ECE but **worsened Brier** and reduced recall.  
> Production continues to use `binary_best.joblib` unless a future calibrated artifact clearly wins.

## Risk weights

> Severity labels remained stable across A/B/C configurations; default balanced weights retained.

## Drift (train vs test)

> No feature exceeded the selected PSI ≥ 0.2 flagging threshold between the training and IID test split.
