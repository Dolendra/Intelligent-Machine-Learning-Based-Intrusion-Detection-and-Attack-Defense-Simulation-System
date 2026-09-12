"""Cross-dataset evaluation scaffold (CSE-CIC-IDS2018 or compatible).

If an external dataset directory is not present, writes a skipped report.
When present, expects ML-ready flow CSVs similar to CICIDS2017 columns.
"""
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
    external = Path(cfg.get("research", {}).get("external_dataset_dir", "CSE-CIC-IDS2018"))
    if not external.is_absolute():
        external = ROOT / external

    report = {
        "experiment": "cross_dataset_validation",
        "train_dataset": "CICIDS2017",
        "external_dataset_dir": str(external),
        "status": "skipped",
        "reason": None,
        "note": (
            "Place a compatible CSE-CIC-IDS2018 (or similar) ML flow export in the configured directory, "
            "then extend this script to map labels/features and score binary_best.joblib under distribution shift."
        ),
    }
    if not external.exists():
        report["reason"] = "External dataset directory not found"
    else:
        csvs = list(external.glob("*.csv"))
        report["csv_files_found"] = len(csvs)
        if not csvs:
            report["reason"] = "Directory exists but contains no CSV files"
        else:
            report["status"] = "ready_for_implementation"
            report["reason"] = (
                "CSVs detected. Full cross-dataset scoring requires schema alignment with CICIDS2017 features "
                "and is left as an explicit research extension."
            )

    path = out_dir / "cross_dataset_status.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {path} status={report['status']}")


if __name__ == "__main__":
    main()
