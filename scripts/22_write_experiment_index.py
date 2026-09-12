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
    ("EXP-001", "baseline_training", "training_report.json", "Model selection + test metrics"),
    ("EXP-002", "feature_selector", "feature_selector_experiment.json", "Dual vs shared SelectKBest"),
    ("EXP-003", "calibration_hpo", "calibration_hpo_report.json", "Calibration / HPO sample experiment"),
    ("EXP-004", "threshold", "threshold_sweep.json", "Operating threshold + uncertainty bands"),
    ("EXP-005", "risk_sensitivity", "risk_weight_sensitivity.json", "Risk weight configurations"),
    ("EXP-006", "xai_agreement", "xai_agreement_report.json", "SHAP vs LIME agreement"),
    ("EXP-007", "scenario_aware", "scenario_aware_evaluation.json", "IID / regime / family slices"),
    ("EXP-008", "drift", "drift_report.json", "Feature/label drift vs train"),
    ("EXP-009", "cross_dataset", "cross_dataset_status.json", "External dataset status/score"),
    ("EXP-010", "label_audit", "label_audit_report.json", "Label map + rare-class audit"),
    ("EXP-011", "error_analysis", "error_analysis_report.json", "Confusion / error analysis"),
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
        path = out_dir / filename
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
