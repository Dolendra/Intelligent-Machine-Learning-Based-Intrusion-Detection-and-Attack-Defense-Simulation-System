"""Re-aggregate open-set experiment records into summaries (mean ± 95% CI, Wilcoxon,
per-family recall, warm-up adaptation). Safe to run while experiments are still going:
it only reads ``openset_<protocol>_records.json`` and rewrites the matching summary.

Usage:  python scripts/53_summarize_research.py [--protocol loafo temporal cross]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import warnings  # noqa: E402

warnings.filterwarnings("ignore", category=RuntimeWarning)

from research.data import ARTIFACT_DIR  # noqa: E402
from research.protocols import summarize  # noqa: E402

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("exp50", ROOT / "scripts" / "50_openset_experiments.py")
_exp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_exp)  # reuse its NaN-safe JSON writer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", nargs="+", default=["loafo", "temporal", "cross", "cross_v2", "cross_perday"])
    args = ap.parse_args()
    for proto in args.protocol:
        # "cross_v2" = cross-dataset records on the corrected 2018 sample (openset_cross_records_v2.json)
        stem, _, ver = proto.partition("_v")
        rec_name = f"openset_{stem}_records_v{ver}.json" if ver.isdigit() else f"openset_{proto}_records.json"
        sum_name = rec_name.replace("_records", "_summary")
        rec_path = ARTIFACT_DIR / rec_name
        if not rec_path.exists():
            print(f"{proto}: no records yet")
            continue
        payload = json.loads(rec_path.read_text(encoding="utf-8"))
        records = payload["records"]
        if not records:
            print(f"{proto}: empty")
            continue
        summary = summarize(records)
        summary["meta"] = {**payload.get("meta", {}), "n_records": len(records),
                           "seeds": sorted({r["seed"] for r in records}),
                           "summarized_at": datetime.now(timezone.utc).isoformat()}
        _exp._write(ARTIFACT_DIR / sum_name, summary)
        seeds = sorted({r["seed"] for r in records})
        folds = sorted({r["fold"] for r in records})
        print(f"{proto}: {len(records)} records, seeds={seeds}, folds={folds}")


if __name__ == "__main__":
    main()
