# Experiment index

Generated: `2026-09-12T19:14:56.174373+00:00`  
Git commit: `98e5376`

| ID | Name | Artifact | Present | Focus |
|----|------|----------|---------|-------|
| EXP-001 | baseline_training | `training_report.json` | yes | Model selection + IID test metrics |
| EXP-002 | feature_selector | `feature_selector_experiment.json` | no | Dual vs shared SelectKBest |
| EXP-003 | calibration_hpo | `calibration_hpo_experiment.json` | yes | Calibration / HPO sample experiment |
| EXP-004 | threshold | `threshold_operating_point.json` | yes | Operating threshold + confidence bands |
| EXP-005 | risk_sensitivity | `risk_weight_sensitivity.json` | yes | Risk weight configurations |
| EXP-006 | xai_agreement | `xai_agreement_report.json` | no | SHAP vs LIME agreement |
| EXP-007 | scenario_aware | `scenario_aware_evaluation.json` | no | IID / regime / family slices |
| EXP-008 | drift | `drift_report.json` | yes | Feature/label drift vs train (IID) — see `DATA_DRIFT.md` |
| EXP-009 | cross_dataset | `cross_dataset_status.json` | yes | External dataset status/score (future work if no dataset) |
| EXP-010 | label_audit | `label_audit_report.json` | no | Label map + rare-class audit |
| EXP-011 | error_analysis | `error_analysis_report.json` | yes | Confusion / error analysis — see `ERROR_ANALYSIS.md` |
| EXP-012 | global_shap | `global_shap_summary.json` | yes | Global + attack-specific importance |
| EXP-013 | temporal_holdout | `temporal_holdout_report.json` | yes | Day-aware Friday holdout vs IID — see `TEMPORAL_HOLDOUT.md` |
| EXP-014 | model_metadata | `model_metadata.json` | yes | Git/config/package reproducibility metadata |
| EXP-015 | intensity_reference | `intensity_reference.json` | yes | Train percentile intensity reference |
| EXP-016 | experiment_index | `experiment_index.json` | yes | Unified experiment catalog |
