"""Committed dataset summary (R1b): per-family and per-day flow counts of the research corpora.

The research caches under research_artifacts/cache/ are git-ignored (large, regenerable), so the
publication tables cannot cite them directly. This script writes the counts they need to
research_artifacts/dataset_summary.json, which is committed.

    python scripts/61_dataset_summary.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from research.data import ARTIFACT_DIR, CACHE_DIR, CIC2018_CACHE, feature_columns, load_cic2017, load_cic2018  # noqa: E402


PROFILE_FEATURES = ["Flow Bytes/s", "Fwd Packets/s", "Init_Win_bytes_forward", "Flow Duration"]


def _benign_profile(df) -> dict:
    """Per-day medians of a few volume features over BENIGN flows (used to document anomalous days)."""
    b = df[df["family"].astype(str) == "BENIGN"]
    return {str(day): {f: float(g[f].median()) for f in PROFILE_FEATURES}
            for day, g in b.groupby(b["day"].astype(str))}


def _counts(df) -> dict:
    by_family = df["family"].astype(str).value_counts().to_dict()
    by_day = {}
    for (day, fam), n in df.groupby([df["day"].astype(str), df["family"].astype(str)]).size().items():
        by_day.setdefault(day, {})[fam] = int(n)
    return {"rows": int(len(df)), "by_family": {k: int(v) for k, v in by_family.items()}, "by_day_family": by_day}


def main() -> None:
    d17 = load_cic2017()
    feats = feature_columns(d17)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cic2017": {**_counts(d17), "n_features": len(feats),
                    "note": "MachineLearningCVE, cleaned and de-duplicated (research cache, research/data.py)"},
    }
    for version, name in CIC2018_CACHE.items():
        if (CACHE_DIR / name).exists():
            d18 = load_cic2018(feats, version=version)
            out[f"cic2018_v{version}"] = {**_counts(d18), "benign_median_by_day": _benign_profile(d18)}
    out["cic2018_note"] = ("v1 = pre-R1b sample (global per-label cap; benign from 4 of 10 days only); "
                           "v2 = R1b sample (5% benign of every day; attacks capped per day and label at random)")
    (ARTIFACT_DIR / "dataset_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print({k: v["rows"] for k, v in out.items() if isinstance(v, dict) and "rows" in v})


if __name__ == "__main__":
    main()
