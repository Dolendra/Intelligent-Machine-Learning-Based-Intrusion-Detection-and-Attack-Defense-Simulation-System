# Experiment index

Generated: `2026-11-09T17:48:55.829833+00:00`  
Git commit: `775e9a9`

| ID | Name | Artifact | Present | Focus |
|----|------|----------|---------|-------|
| EXP-001 | baseline_training | `training_report.json` | yes | Model selection + IID test metrics |
| EXP-002 | feature_selector | `feature_selector_experiment.json` | no | Dual vs shared SelectKBest |
| EXP-003 | calibration_hpo | `calibration_hpo_experiment.json` | yes | Calibration / HPO sample experiment |
| EXP-004 | threshold | `threshold_operating_point.json` | yes | Operating threshold + confidence bands |
| EXP-005 | risk_sensitivity | `risk_weight_sensitivity.json` | yes | Risk weight configurations |
| EXP-006 | xai_agreement | `xai_agreement_report.json` | no | SHAP vs LIME agreement |
| EXP-007 | scenario_aware | `scenario_aware_evaluation.json` | no | IID / regime / family slices |
| EXP-008 | drift | `drift_report.json` | yes | Feature/label drift vs train (IID) |
| EXP-009 | cross_dataset | `cross_dataset_status.json` | yes | External dataset status/score |
| EXP-010 | label_audit | `label_audit_report.json` | no | Label map + rare-class audit |
| EXP-011 | error_analysis | `error_analysis_report.json` | yes | Confusion / error analysis |
| EXP-012 | global_shap | `global_shap_summary.json` | yes | Global + attack-specific importance |
| EXP-013 | temporal_holdout | `temporal_holdout_report.json` | yes | Friday slice scored by frozen models (trained on all days - NOT a true temporal test; superseded by EXP-022) |
| EXP-014 | model_metadata | `model_metadata.json` | yes | Git/config/package reproducibility metadata |
| EXP-015 | intensity_reference | `intensity_reference.json` | yes | Train percentile intensity reference |
| EXP-016 | experiment_index | `experiment_index.json` | yes | Unified experiment catalog |
| EXP-017 | generalization_p10 | `generalization_report.json` | yes | P10 IID vs temporal generalization (frozen) |
| EXP-018 | empirical_mitigation_ddos | `empirical_mitigation_report.json` | yes | P11 measured mitigation DDoS BLOCK_SOURCE (CONTROLLED) |
| EXP-019 | empirical_mitigation_dos | `empirical_mitigation_report.json` | yes | P11 measured mitigation DoS RATE_LIMIT (CONTROLLED) |
| EXP-020 | final_security_validation | `final_security_validation_report.json` | yes | P12 final security validation gate |
| EXP-021 | openset_loafo | `research_artifacts/openset_loafo_summary.json` | yes | Aegis-OSR vs baselines, leave-one-attack-family-out, 5 seeds, CIs + Wilcoxon |
| EXP-022 | openset_temporal_true | `research_artifacts/openset_temporal_summary.json` | no | True temporal split (retrained on earlier days) + label-light recalibration |
| EXP-023 | openset_cross_dataset | `research_artifacts/openset_cross_summary.json` | no | CICIDS2017 -> CSE-CIC-IDS2018 open-set transfer + recalibration |
| EXP-024 | zero_day_gate | `research_artifacts/zero_day_gate_report.json` | yes | Production Zero-Day Gate operating points vs frozen v1.1 (advisory) |
| EXP-025 | pilot_fusion_selection | `research_artifacts/pilot_seed0_fusion_selection.csv` | yes | Seed-0 pilot that selected Fisher fusion + kNN novelty (excluded from reported results) |
