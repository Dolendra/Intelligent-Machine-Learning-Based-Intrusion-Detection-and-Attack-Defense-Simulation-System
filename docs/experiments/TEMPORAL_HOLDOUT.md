# Temporal / day-aware holdout

Script: `scripts/25_temporal_holdout_eval.py`  
Plots: `scripts/28_plot_temporal_generalization.py`  
Artifact: `models/trained_models/temporal_holdout_report.json`  
Figures: `models/trained_models/figures/temporal_*.png`

## Protocol

- Sample day-named CICIDS2017 MachineLearningCVE CSVs (cap per file)
- Score the **frozen** Decision Tree / Random Forest joblibs (**no retrain**)
- Compare:
  - **IID stratified test** metrics from `training_report.json`
  - **Friday temporal holdout** samples
  - Mon–Thu early-day reference samples

## Freeze snapshot (v1.1)

| Slice | n | Attack rate | Binary F1 | Notes |
|-------|--:|------------:|----------:|-------|
| IID test | 504,151 | ~16.9% | 0.99048 | Full stratified test |
| Friday | 36,000 | 33.8% | 0.99770 | Δ F1 (IID−Fri) = −0.00722 |
| Mon–Thu | 60,000 | 6.9% | 0.97997 | Δ F1 (IID−early) = +0.01051 |

Friday multiclass scored **Bot / DDoS / PortScan** only (absent: BruteForce, DoS, WebAttack). Perfect subset F1 ≠ six-class temporal proof.

## How to cite

Report IID metrics as:

> Performance on the stratified IID holdout

and temporal metrics as:

> Performance under a day-aware (Friday) holdout sample of the frozen models

Do **not** claim equivalent production generalization from IID numbers alone.  
Do **not** claim full six-class temporal multiclass success from the Friday subset.

External-dataset validation was not performed within the current experimental scope and is identified as future work for assessing cross-dataset generalization.

## P10 consolidation

Full generalization write-up (IID vs temporal degradation, class-wise, temporal PSI, research vs production):  
**`docs/GENERALIZATION.md`** · artifact `generalization_report.json` (EXP-017) · `scripts/41_generalization_report.py`
