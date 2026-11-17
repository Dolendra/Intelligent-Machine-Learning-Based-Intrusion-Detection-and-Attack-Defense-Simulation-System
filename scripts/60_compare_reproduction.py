"""Compare original experiment records with an independent re-run (R1a reproducibility check).

    python scripts/50_openset_experiments.py --protocol loafo --seeds 1 2 3 4 5 --tag repro
    python scripts/60_compare_reproduction.py --protocol loafo --tag repro

Writes research_artifacts/reproduction_<protocol>_<tag>.json with per-metric maximum absolute
differences and the headline (proposed vs closed-set XGB) for both runs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402

from research.data import ARTIFACT_DIR  # noqa: E402
from research.openset import PROPOSED  # noqa: E402

METRICS = ["zero_day_recall", "auroc_unknown", "known_recall", "fpr"]


def _load(path: Path) -> dict:
    recs = json.loads(path.read_text(encoding="utf-8"))["records"]
    return {(r["fold"], r["seed"]): r for r in recs}


def _headline(recs: dict, method: str) -> float:
    seeds = sorted({s for _, s in recs})
    return float(np.mean([np.mean([r["methods"][method]["zero_day_recall"] for (f, s), r in recs.items() if s == seed])
                          for seed in seeds]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", default="loafo")
    ap.add_argument("--tag", default="repro")
    ap.add_argument("--tolerance", type=float, default=0.005, help="max |diff| accepted as reproduced")
    a = ap.parse_args()
    orig = _load(ARTIFACT_DIR / f"openset_{a.protocol}_records.json")
    rep = _load(ARTIFACT_DIR / f"openset_{a.protocol}_records_{a.tag}.json")
    common = sorted(set(orig) & set(rep))
    missing = sorted(set(orig) - set(rep))
    methods = list(next(iter(orig.values()))["methods"])
    diffs: dict[str, dict[str, float]] = {}
    exact = 0
    total = 0
    for m in methods:
        diffs[m] = {}
        for k in METRICS:
            d = [abs((orig[c]["methods"][m][k] or 0) - (rep[c]["methods"][m][k] or 0)) for c in common
                 if orig[c]["methods"][m][k] is not None and rep[c]["methods"][m][k] is not None]
            diffs[m][k] = float(max(d)) if d else float("nan")
            exact += sum(x == 0 for x in d)
            total += len(d)
    worst_proposed = max(diffs[PROPOSED].values())
    result = {
        "protocol": a.protocol,
        "tag": a.tag,
        "pairs_compared": len(common),
        "pairs_missing_in_rerun": [list(c) for c in missing],
        "exactly_equal_values": f"{exact}/{total}",
        "max_abs_diff": diffs,
        "headline_original": {"proposed": _headline(orig, PROPOSED), "closed_set_xgb": _headline(orig, "Closed-set XGB")},
        "headline_rerun": {"proposed": _headline({c: rep[c] for c in common}, PROPOSED),
                           "closed_set_xgb": _headline({c: rep[c] for c in common}, "Closed-set XGB")},
        "tolerance": a.tolerance,
        "reproduced": bool(not missing and worst_proposed <= a.tolerance),
        "note": "Same code, data, seeds and configuration; any non-zero difference would point to "
                "non-deterministic training (e.g. multi-threaded PyTorch in the autoencoder baseline).",
    }
    out = ARTIFACT_DIR / f"reproduction_{a.protocol}_{a.tag}.json"
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("pairs_compared", "exactly_equal_values", "headline_original",
                                              "headline_rerun", "reproduced")}, indent=1))
    print("max |diff| for proposed:", diffs[PROPOSED])
    print("largest |diff| by method:", {m: round(max(v.values()), 4) for m, v in diffs.items()})


if __name__ == "__main__":
    main()
