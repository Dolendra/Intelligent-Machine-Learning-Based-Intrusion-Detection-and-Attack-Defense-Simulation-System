# Experiment index

Generated: `2026-09-12T19:05:51.932951+00:00`  
Git commit: `c99d2d3`

| ID | Name | Artifact | Present | Focus |
|----|------|----------|---------|-------|
| EXP-001 | baseline_training | `training_report.json` | yes | Model selection + test metrics |
| EXP-002 | feature_selector | `feature_selector_experiment.json` | no | Dual vs shared SelectKBest |
| EXP-003 | calibration_hpo | `calibration_hpo_report.json` | no | Calibration / HPO sample experiment |
| EXP-004 | threshold | `threshold_sweep.json` | yes | Operating threshold + uncertainty bands |
| EXP-005 | risk_sensitivity | `risk_weight_sensitivity.json` | yes | Risk weight configurations |
| EXP-006 | xai_agreement | `xai_agreement_report.json` | no | SHAP vs LIME agreement |
| EXP-007 | scenario_aware | `scenario_aware_evaluation.json` | no | IID / regime / family slices |
| EXP-008 | drift | `drift_report.json` | yes | Feature/label drift vs train |
| EXP-009 | cross_dataset | `cross_dataset_status.json` | yes | External dataset status/score |
| EXP-010 | label_audit | `label_audit_report.json` | no | Label map + rare-class audit |
| EXP-011 | error_analysis | `error_analysis_report.json` | yes | Confusion / error analysis |
| EXP-012 | global_shap | `global_shap_summary.json` | yes | Global + attack-specific importance |
