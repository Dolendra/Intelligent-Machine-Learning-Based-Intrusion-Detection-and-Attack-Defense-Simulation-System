"""Build a unified experiment index from known research artifacts."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path

EXPERIMENTS = [
    # Core ML / research
    ("EXP-001", "baseline_training", "training_report.json", "Model selection + IID test metrics"),
    ("EXP-002", "feature_selector", "feature_selector_experiment.json", "Dual vs shared SelectKBest"),
    ("EXP-003", "calibration_hpo", "calibration_hpo_experiment.json", "Calibration / HPO sample experiment"),
    ("EXP-004", "threshold", "threshold_operating_point.json", "Operating threshold + confidence bands"),
    ("EXP-005", "risk_sensitivity", "risk_weight_sensitivity.json", "Risk weight configurations"),
    ("EXP-006", "xai_agreement", "xai_agreement_report.json", "SHAP vs LIME agreement"),
    ("EXP-007", "scenario_aware", "scenario_aware_evaluation.json", "IID / regime / family slices"),
    ("EXP-008", "drift", "drift_report.json", "Feature/label drift vs train (IID)"),
    ("EXP-009", "cross_dataset", "cross_dataset_status.json", "External dataset status/score"),
    ("EXP-010", "label_audit", "label_audit_report.json", "Label map + rare-class audit"),
    ("EXP-011", "error_analysis", "error_analysis_report.json", "Confusion / error analysis"),
    ("EXP-012", "global_shap", "global_shap_summary.json", "Global + attack-specific importance"),
    ("EXP-013", "temporal_holdout", "temporal_holdout_report.json",
     "Friday slice scored by frozen models (trained on all days - NOT a true temporal test; superseded by EXP-022)"),
    # Reproducibility / application verification
    ("EXP-014", "model_metadata", "model_metadata.json", "Git/config/package reproducibility metadata"),
    ("EXP-015", "intensity_reference", "intensity_reference.json", "Train percentile intensity reference"),
    ("EXP-016", "experiment_index", "experiment_index.json", "Unified experiment catalog"),
    ("EXP-017", "generalization_p10", "generalization_report.json", "P10 IID vs temporal generalization (frozen)"),
    ("EXP-018", "empirical_mitigation_ddos", "empirical_mitigation_report.json", "P11 measured mitigation DDoS BLOCK_SOURCE (CONTROLLED)"),
    ("EXP-019", "empirical_mitigation_dos", "empirical_mitigation_report.json", "P11 measured mitigation DoS RATE_LIMIT (CONTROLLED)"),
    ("EXP-020", "final_security_validation", "final_security_validation_report.json", "P12 final security validation gate"),
    # v3 open-set research track (paths containing "/" resolve from the repo root)
    ("EXP-021", "openset_loafo", "research_artifacts/openset_loafo_summary.json",
     "Aegis-OSR vs baselines, leave-one-attack-family-out, 5 seeds, CIs + Wilcoxon"),
    ("EXP-022", "openset_temporal_true", "research_artifacts/openset_temporal_summary.json",
     "True temporal split (retrained on earlier days) + label-light recalibration"),
    ("EXP-023", "openset_cross_dataset", "research_artifacts/openset_cross_summary.json",
     "CICIDS2017 -> CSE-CIC-IDS2018 open-set transfer + recalibration"),
    ("EXP-024", "zero_day_gate", "research_artifacts/zero_day_gate_report.json",
     "Production Zero-Day Gate operating points vs frozen v1.1 (advisory)"),
    ("EXP-025", "pilot_fusion_selection", "research_artifacts/pilot_seed0_fusion_selection.csv",
     "Seed-0 pilot that selected Fisher fusion + kNN novelty (excluded from reported results)"),
]


def _git_commit() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return None


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = ROOT / "docs" / "experiments"
    docs_dir.mkdir(parents=True, exist_ok=True)

    items = []
    for eid, name, filename, conclusion in EXPERIMENTS:
        path = (ROOT / filename) if "/" in filename else (out_dir / filename)
        items.append(
            {
                "experiment_id": eid,
                "name": name,
                "artifact": filename,
                "present": path.exists(),
                "path": str(path) if path.exists() else None,
                "intended_conclusion": conclusion,
            }
        )

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "model_version": cfg.get("models", {}).get("model_version"),
        "experiments": items,
        "note": "Index of research artifacts — run the corresponding scripts to populate missing files.",
    }
    out_json = out_dir / "experiment_index.json"
    out_json.write_text(json.dumps(index, indent=2), encoding="utf-8")

    lines = [
        "# Experiment index",
        "",
        f"Generated: `{index['generated_at']}`  ",
        f"Git commit: `{index.get('git_commit') or 'n/a'}`",
        "",
        "| ID | Name | Artifact | Present | Focus |",
        "|----|------|----------|---------|-------|",
    ]
    for it in items:
        lines.append(
            f"| {it['experiment_id']} | {it['name']} | `{it['artifact']}` | "
            f"{'yes' if it['present'] else 'no'} | {it['intended_conclusion']} |"
        )
    lines.append("")
    (docs_dir / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {docs_dir / 'INDEX.md'}")


if __name__ == "__main__":
    main()
