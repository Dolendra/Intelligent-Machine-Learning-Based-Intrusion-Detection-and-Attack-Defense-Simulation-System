# IID data-drift monitoring

Script: `scripts/20_data_drift_report.py`  
Plots: `scripts/29_plot_drift_and_errors.py`  
Artifact: `models/trained_models/drift_report.json`  
Figures: `drift_psi_train_vs_test.png`, `drift_label_distribution.png`

## Protocol

- Reference: processed **train** split  
- Current: processed **test** split (IID stratified)  
- Feature PSI + mean-shift diagnostics; label % deltas  
- Heuristic: PSI ≥ 0.2 → notable shift (not a universal rule)

## Freeze snapshot (v1.1)

| Item | Value |
|------|------:|
| Features compared | 78 |
| Flagged PSI ≥ 0.2 | **0** |
| Max PSI (listed) | **0.0** |
| Label Δ pp (all classes) | **≈ 0.0** |
| Retrain recommendation | `monitor` (`promote: false`) |

## How to cite

> Under the stratified IID train→test check, no high-PSI feature shifts were flagged.

Do **not** cite this as proof of temporal or live-network drift absence. Pair with the Friday temporal holdout (§8 / `TEMPORAL_HOLDOUT.md`).
