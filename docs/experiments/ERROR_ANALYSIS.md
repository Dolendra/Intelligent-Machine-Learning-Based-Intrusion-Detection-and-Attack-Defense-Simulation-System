# Error analysis (residual confusions)

Script: `scripts/23_error_analysis.py`  
Plots: `scripts/29_plot_drift_and_errors.py`  
Artifact: `models/trained_models/error_analysis_report.json`  
Figures: `error_binary_fp_fn_counts.png`, `error_multiclass_top_confusions.png`  
Notebook: `notebooks/06_error_analysis.ipynb`

## Protocol

Surfaces frozen IID test confusion counts from `training_report.json` (Decision Tree binary / Random Forest multiclass). Does not retrain.

## Freeze snapshot (v1.1)

### Binary (Decision Tree @ 0.85)

| | Count |
|--|------:|
| TN | 417,635 |
| FP | **1,377** |
| FN | **255** |
| TP | 84,884 |
| FPR | 0.00329 |
| FNR | 0.00300 |

### Multiclass (attack-only RF)

- **18** off-diagonal errors on **85,139** attack flows  
- Dominant: PortScan→DoS (6), PortScan→WebAttack (3), DoS→WebAttack (3), plus smaller DoS/PortScan/WebAttack / BruteForce→DoS swaps  
- Bot and DDoS diagonals are perfect on the IID test CM in this freeze

## How to cite

> Residual errors are rare under the IID test split; remaining multiclass confusion concentrates among PortScan / DoS / WebAttack.

Do **not** claim zero operational false alarms under live traffic.
