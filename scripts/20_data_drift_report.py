"""Detect feature/label drift between training reference and a comparison split.

Default: train vs test (in-project distribution check).
Optional: compare against an uploaded/current sample parquet/CSV path via --current.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path
from ml.evaluation.drift import feature_drift_report, label_drift_report
from ml.preprocessing.dataset import get_feature_columns, load_processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Feature/label drift report")
    parser.add_argument("--ref", default="train", help="Processed split name for reference")
    parser.add_argument("--current", default="test", help="Processed split name OR path to CSV/parquet")
    args = parser.parse_args()

    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    ref = load_processed(args.ref)
    cur_path = Path(args.current)
    if cur_path.exists():
        if cur_path.suffix.lower() == ".parquet":
            import pandas as pd

            cur = pd.read_parquet(cur_path)
        else:
            import pandas as pd

            cur = pd.read_csv(cur_path, low_memory=False)
            cur.columns = [c.strip() for c in cur.columns]
    else:
        cur = load_processed(args.current)

    feats = [c for c in get_feature_columns(ref) if c in cur.columns]
    report = {
        "experiment": "data_drift",
        "ref": args.ref,
        "current": args.current,
        "feature_drift": feature_drift_report(ref, cur, feats),
        "label_drift": label_drift_report(ref["Label"], cur["Label"]) if "Label" in cur.columns else None,
        "retrain_recommendation": None,
        "note": "Prototype drift monitoring — does not auto-replace production models.",
    }
    flagged = report["feature_drift"]["flagged_psi_ge_0.2"]
    if len(flagged) >= 5:
        report["retrain_recommendation"] = {
            "action": "review_and_retrain_candidate",
            "reason": f"{len(flagged)} features with PSI>=0.2 vs reference",
            "promote": False,
        }
    else:
        report["retrain_recommendation"] = {
            "action": "monitor",
            "reason": "Few or no high-PSI features",
            "promote": False,
        }

    path = out_dir / "drift_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    print(f"Flagged features: {len(flagged)}; recommendation={report['retrain_recommendation']['action']}")


if __name__ == "__main__":
    main()
