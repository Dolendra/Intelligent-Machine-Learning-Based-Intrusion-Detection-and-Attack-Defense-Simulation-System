"""Build the leakage-free replay pool for the Live Monitor, Cyber Range and XAI studies.

A flow is eligible only if its 77 feature values (float32, exact) are

* in the **frozen v1.1 test split**  (data/processed/test.parquet), and
* in the **Zero-Day Gate test split** (research cache, stratified_split seed 42), and
* in **neither** model's training or validation split.

Before R1a the pool was drawn from the gate's test split only; ~70 % of those rows were in the
frozen model's *training* split because the two models use independent random splits. That pool
is kept at research_artifacts/replay/legacy/ as evidence and must not be used for frozen-model
evaluation (see docs/research/CLAIM_AUDIT.md §0.2).

Infiltration and Heartbleed are included in full: the frozen pipeline drops them as rare classes
(< 50 rows) and the gate excludes them, so neither model ever trained on them. This is asserted.

Outputs:
  research_artifacts/replay/replay_pool.parquet
  research_artifacts/replay/replay_pool_manifest.json   (counts, overlap checks, hashes)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from research.data import ARTIFACT_DIR, feature_columns, load_cic2017, stratified_split  # noqa: E402

SEED = 42
PER_FAMILY = 700
BENIGN_N = 8000
NATURAL_UNKNOWN = ["Infiltration", "Heartbleed"]
PROCESSED = ROOT / "data" / "processed"
OUT = ARTIFACT_DIR / "replay"


def row_keys(df: pd.DataFrame, feats: list[str]) -> np.ndarray:
    """Exact row identity on the shared feature set (float32 to match the research cache)."""
    X = df[feats].to_numpy(dtype=np.float32)
    X = X + np.float32(0.0)  # normalize -0.0 → 0.0
    return pd.util.hash_pandas_object(pd.DataFrame(X), index=False).to_numpy()


def main() -> None:
    df = load_cic2017()
    feats = feature_columns(df)
    base = df[~df["family"].isin(NATURAL_UNKNOWN)]
    g_tr, g_va, g_te = stratified_split(base, (0.7, 0.1, 0.2), SEED)

    frozen = {s: pd.read_parquet(PROCESSED / f"{s}.parquet", columns=feats) for s in ("train", "val", "test")}
    fk = {s: set(row_keys(d, feats)) for s, d in frozen.items()}
    gate_seen = set(row_keys(g_tr, feats)) | set(row_keys(g_va, feats))

    te_keys = row_keys(g_te, feats)
    in_frozen_test = np.isin(te_keys, list(fk["test"]))
    in_frozen_seen = np.isin(te_keys, list(fk["train"] | fk["val"]))
    in_gate_seen = np.isin(te_keys, list(gate_seen))
    eligible_mask = in_frozen_test & ~in_frozen_seen & ~in_gate_seen
    eligible = g_te[eligible_mask]

    unseen = df[df["family"].isin(NATURAL_UNKNOWN)]
    u_keys = row_keys(unseen, feats)
    all_frozen = fk["train"] | fk["val"] | fk["test"]
    assert not np.isin(u_keys, list(all_frozen)).any(), "unseen families found in frozen splits"
    assert not np.isin(u_keys, list(gate_seen)).any(), "unseen families found in gate training data"

    parts, avail, taken = [], {}, {}
    for fam, g in eligible.groupby("family", observed=True):
        n = BENIGN_N if fam == "BENIGN" else PER_FAMILY
        avail[str(fam)] = int(len(g))
        pick = g.sample(n=min(n, len(g)), random_state=SEED)
        taken[str(fam)] = int(len(pick))
        parts.append(pick)
    parts.append(unseen)
    for fam in NATURAL_UNKNOWN:
        avail[fam] = taken[fam] = int((unseen["family"] == fam).sum())
    pool = pd.concat(parts, ignore_index=True)

    # ---- independent re-check on the final pool (the acceptance test repeats this)
    pk = row_keys(pool, feats)
    overlap = {
        "frozen_train": int(np.isin(pk, list(fk["train"])).sum()),
        "frozen_val": int(np.isin(pk, list(fk["val"])).sum()),
        "gate_train_or_val": int(np.isin(pk, list(gate_seen)).sum()),
    }
    assert all(v == 0 for v in overlap.values()), overlap

    pool["Fwd Header Length.1"] = pool["Fwd Header Length"]  # frozen v1.1 schema column
    for c in ("day", "fine_label", "family", "dataset"):
        pool[c] = pool[c].astype(str)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "replay_pool.parquet"
    pool.drop(columns=["seq", "is_attack"]).to_parquet(path, index=False, compression="zstd")

    manifest = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rule": "frozen v1.1 test split ∩ gate test split, minus any row seen in either model's train/val "
                "(exact float32 match on 77 features); plus all Infiltration/Heartbleed (never trained on)",
        "seed": SEED,
        "gate_test_rows": int(len(g_te)),
        "gate_test_rows_in_frozen_test": int(in_frozen_test.sum()),
        "gate_test_rows_in_frozen_train_or_val": int(in_frozen_seen.sum()),
        "eligible_rows": int(eligible_mask.sum()),
        "available_per_family": avail,
        "sampled_per_family": taken,
        "overlap_check": overlap,
        "rows": int(len(pool)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "supersedes": "legacy/replay_pool_v1_INVALID_for_frozen.parquet (~70% in frozen train split)",
    }
    (OUT / "replay_pool_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("eligible_rows", "available_per_family", "sampled_per_family",
                                                 "overlap_check", "rows")}, indent=1))


if __name__ == "__main__":
    main()
