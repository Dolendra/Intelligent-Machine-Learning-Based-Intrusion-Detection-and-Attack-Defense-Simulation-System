"""Confusion-matrix style error analysis from training artifacts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "experiment": "error_analysis",
        "status": "ok",
        "guidance": (
            "Prefer per-class precision/recall from training_report; "
            "re-run after attack-only Stage-2 retrain for family-level confusion."
        ),
    }

    tr = out_dir / "training_report.json"
    if not tr.exists():
        report["status"] = "skipped"
        report["reason"] = "training_report.json missing — train models first"
    else:
        data = json.loads(tr.read_text(encoding="utf-8"))
        report["source"] = "training_report.json"
        report["binary"] = data.get("binary") or data.get("binary_metrics") or data.get("binary_best")
        report["multiclass"] = data.get("multiclass") or data.get("multiclass_metrics") or data.get("multiclass_best")
        # Surface common failure modes if present in nested reports
        for key in ("confusion_matrix", "classification_report", "per_class", "errors"):
            if isinstance(report["binary"], dict) and key in report["binary"]:
                report[f"binary_{key}"] = report["binary"][key]
            if isinstance(report["multiclass"], dict) and key in report["multiclass"]:
                report[f"multiclass_{key}"] = report["multiclass"][key]

    out_path = out_dir / "error_analysis_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out_path), "status": report["status"]}, indent=2))


if __name__ == "__main__":
    main()
