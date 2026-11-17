"""R1a acceptance: replay flows must never overlap either model's training/validation data.

The check needs the local (git-ignored) frozen splits and research cache; it skips in CI when they
are absent. The manifest-level assertions always run.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "research_artifacts" / "replay"
POOL = REPLAY / "replay_pool.parquet"
MANIFEST = REPLAY / "replay_pool_manifest.json"
PROCESSED = ROOT / "data" / "processed"
CACHE = ROOT / "research_artifacts" / "cache" / "cic2017.parquet"


def test_manifest_records_zero_overlap_and_matches_pool():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["version"] >= 2
    assert all(v == 0 for v in m["overlap_check"].values()), m["overlap_check"]
    assert hashlib.sha256(POOL.read_bytes()).hexdigest() == m["sha256"], "pool changed without manifest"
    pool = pd.read_parquet(POOL, columns=["family"])
    counts = pool["family"].value_counts().to_dict()
    assert counts == m["sampled_per_family"]


@pytest.mark.skipif(not (PROCESSED / "train.parquet").exists() or not CACHE.exists(),
                    reason="needs local data/processed splits and research cache")
def test_pool_has_no_rows_from_any_training_or_validation_split():
    from research.data import feature_columns, load_cic2017, stratified_split

    spec = __import__("importlib.util").util.spec_from_file_location("b52", ROOT / "scripts" / "52_build_replay_pool.py")
    b52 = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(b52)

    df = load_cic2017()
    feats = feature_columns(df)
    pool_keys = b52.row_keys(pd.read_parquet(POOL), feats)
    for split in ("train", "val"):
        seen = set(b52.row_keys(pd.read_parquet(PROCESSED / f"{split}.parquet", columns=feats), feats))
        assert not np.isin(pool_keys, list(seen)).any(), f"replay rows found in frozen {split} split"
    base = df[~df["family"].isin(b52.NATURAL_UNKNOWN)]
    g_tr, g_va, _ = stratified_split(base, (0.7, 0.1, 0.2), b52.SEED)
    gate_seen = set(b52.row_keys(g_tr, feats)) | set(b52.row_keys(g_va, feats))
    assert not np.isin(pool_keys, list(gate_seen)).any(), "replay rows found in gate train/val"
