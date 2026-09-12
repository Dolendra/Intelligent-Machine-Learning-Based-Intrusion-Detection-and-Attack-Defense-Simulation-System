# Temporal / day-aware holdout

Script: `scripts/25_temporal_holdout_eval.py`  
Artifact: `models/trained_models/temporal_holdout_report.json`

## Protocol

- Sample day-named CICIDS2017 MachineLearningCVE CSVs
- Score the **frozen** joblibs (no retrain)
- Compare:
  - **IID stratified test** metrics from `training_report.json`
  - **Friday temporal holdout** samples
  - Mon–Thu early-day reference samples

## How to cite

Report IID metrics as:

> Performance on the stratified IID holdout

and temporal metrics as:

> Performance under a day-aware (Friday) holdout sample

Do **not** claim equivalent production generalization from IID numbers alone.

## Freeze snapshot (sampled)

See `temporal_holdout_report.json` for exact figures. In the freeze run, Friday-sample binary F1 remained competitive with the IID test F1 (delta recorded in the artifact). Mon–Thu early-day samples can differ because day files are attack-composition skewed — discuss composition, not just the headline F1.
