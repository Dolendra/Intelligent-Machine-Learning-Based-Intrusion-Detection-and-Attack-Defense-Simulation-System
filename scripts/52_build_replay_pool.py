"""Build the small replay pool that powers the Live Traffic Monitor.

Flows come from the *test* portion of the same IID split used to train the Zero-Day Gate
(seed 42), so the live demo never replays training data. Infiltration and Heartbleed are
included in full: neither the frozen v1.1 models nor the gate were trained on them, so they
act as genuine unseen attacks in the demo.

Output: research_artifacts/replay/replay_pool.parquet (committed; a few MB).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from research.data import ARTIFACT_DIR, load_cic2017, stratified_split  # noqa: E402

SEED = 42
PER_FAMILY = 700
BENIGN_N = 8000
NATURAL_UNKNOWN = ["Infiltration", "Heartbleed"]


def main() -> None:
    df = load_cic2017()
    base = df[~df["family"].isin(NATURAL_UNKNOWN)]
    _, _, te = stratified_split(base, (0.7, 0.1, 0.2), SEED)
    parts = []
    for fam, g in te.groupby("family", observed=True):
        n = BENIGN_N if fam == "BENIGN" else PER_FAMILY
        parts.append(g.sample(n=min(n, len(g)), random_state=SEED))
    parts.append(df[df["family"].isin(NATURAL_UNKNOWN)])
    pool = pd.concat(parts, ignore_index=True)
    pool["Fwd Header Length.1"] = pool["Fwd Header Length"]  # frozen v1.1 schema column
    for c in ("day", "fine_label", "family", "dataset"):
        pool[c] = pool[c].astype(str)
    out = ARTIFACT_DIR / "replay"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "replay_pool.parquet"
    pool.drop(columns=["seq", "is_attack"]).to_parquet(path, index=False, compression="zstd")
    print(pool["family"].value_counts().to_string())
    print(f"wrote {path} ({path.stat().st_size / 1e6:.2f} MB, {len(pool):,} flows)")


if __name__ == "__main__":
    main()
