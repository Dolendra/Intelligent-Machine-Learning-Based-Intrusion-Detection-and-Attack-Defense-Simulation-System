"""Stage 0 finding: how many float32-identical rows crossed the *historical* splits? (no training)

``research/data._finalize`` de-duplicates at source precision and then casts to float32, so ≈0.9 % of
CICIDS2017 rows are exact float32 duplicates of another row with the same label. This script rebuilds
the historical LOAFO (seeds 1-5) and per-day (seeds 1-5) splits through the unchanged protocol code,
stops before any model is fitted, and counts rows shared between splits.

Writes research_artifacts/r3/duplicate_overlap_audit.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402

import research.protocols as P  # noqa: E402
from research.artifact_guard import R3_DIR, assert_writable  # noqa: E402
from research.data import feature_columns, load_cic2017, load_cic2018  # noqa: E402


class _Stop(Exception):
    pass


def _hashes(df: pd.DataFrame, feats: list[str]) -> pd.Series:
    return pd.util.hash_pandas_object(df[feats + ["fine_label"]], index=False)


def main() -> None:
    out: dict = {"loafo": [], "cross_perday": []}
    df17 = load_cic2017()
    feats = feature_columns(df17)

    def grab(store: list):
        def cb(key: dict, splits: dict) -> None:
            fr = {k: v for k, v in splits.items() if v is not None and len(v)}
            h = {k: _hashes(v, feats) for k, v in fr.items()}
            row = {"fold": key["fold"], "seed": key["seed"], "n": {k: int(len(v)) for k, v in fr.items()}}
            if "test" in h:
                te = h["test"]
                benign = (fr["test"]["family"].astype(str) == "BENIGN").to_numpy()
                for side in [s for s in ("train", "val", "warmup") if s in h]:
                    hit = te.isin(set(h[side])).to_numpy()
                    row[f"test_rows_also_in_{side}"] = int(hit.sum())
                    row[f"test_benign_rows_also_in_{side}"] = int((hit & benign).sum())
                row["test_benign"] = int(benign.sum())
            store.append(row)
            raise _Stop
        return cb

    for seed in range(1, 6):
        for fam in P.LOAFO_FAMILIES:
            try:
                P.loafo(df17, seeds=[seed], families=[fam], log=lambda m: None, on_split=grab(out["loafo"]))
            except _Stop:
                pass
    # per-day: the model is trained before the day loop, so rebuild the day splits with the protocol's own helpers
    df18 = load_cic2018(feats, version=2)
    df18 = df18[feats + [c for c in df18.columns if c not in feats]]
    for seed in range(1, 6):
        for day in sorted(df18["day"].astype(str).unique()):
            day_df = df18[df18["day"].astype(str) == day]
            warm, pool = P._split_warmup(day_df, max(P.WARMUP_WINDOWS))
            test = P._cap_keep_index(pool, P._caps(pool, P.PERDAY_TEST_CAPS), seed).reset_index(drop=True)
            try:
                grab(out["cross_perday"])({"fold": day, "seed": seed}, {"test": test, "warmup": warm})
            except _Stop:
                pass

    def summ(rows, key):
        vals = [r.get(key, 0) for r in rows]
        return {"max": max(vals), "mean": sum(vals) / len(vals)}

    out["summary"] = {
        "loafo": {k: summ(out["loafo"], k) for k in ("test_rows_also_in_train", "test_rows_also_in_val",
                                                     "test_benign_rows_also_in_train", "test_benign_rows_also_in_val",
                                                     "test_benign")},
        "cross_perday": {k: summ(out["cross_perday"], k) for k in ("test_rows_also_in_warmup", "test_benign")},
        "note": "LOAFO val supplies the C1/C2 benign calibration splits; a test benign row with an exact twin in train "
                "or val is not an independent draw. Cross-dataset train/test twins are not counted (different captures).",
    }
    path = R3_DIR / "duplicate_overlap_audit.json"
    assert_writable(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["summary"], indent=1))


if __name__ == "__main__":
    main()
