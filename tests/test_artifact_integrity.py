"""R3 Stage 0 guards: historical artifacts, the frozen v1.1 baseline and per-flow score dumps.

1. Every protected historical artifact is unchanged (SHA-256 manifest).
2. Frozen v1.1 model / threshold / report files are byte-identical to tag v1.1-research.
3. Experiment writers refuse to overwrite protected paths (scripts 50, 54 and the guard itself).
4. Score dumps are passive: a run with a dump gives exactly the same record as a run without,
   and every evaluated flow of every variant has finite evidence-stream scores.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research import artifact_guard as G

ROOT = Path(__file__).resolve().parents[1]


def test_protected_artifacts_unchanged():
    man = G.load_manifest()
    assert len(man["files"]) >= 25, "protected manifest missing or truncated"
    assert G.verify_manifest() == {}, "a historical research artifact was changed or removed"


def test_every_committed_artifact_is_protected():
    unprotected = set(G._committed_artifacts()) - set(G.load_manifest()["files"])
    assert not unprotected, f"committed artifacts missing from PROTECTED_MANIFEST.json: {sorted(unprotected)}"


def test_frozen_v11_identical_to_tag():
    assert G.frozen_v11_diff() == []


@pytest.mark.parametrize("rel", ["research_artifacts/openset_loafo_records.json",
                                 "research_artifacts/frozen_v11_on_cic2018_v2.json",
                                 "models/trained_models/multiclass_best.joblib"])
def test_guard_refuses_protected(rel):
    with pytest.raises(G.ProtectedArtifactError):
        G.assert_writable(ROOT / rel)


def test_guard_allows_new_r3_outputs(tmp_path):
    G.assert_writable(G.R3_DIR / "loafo_records.json")
    G.assert_writable(tmp_path / "anything.json")


def test_experiment_script_refuses_to_overwrite():
    spec = importlib.util.spec_from_file_location("exp50", ROOT / "scripts" / "50_openset_experiments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    before = (ROOT / "research_artifacts/openset_temporal_records.json").read_bytes()
    with pytest.raises(G.ProtectedArtifactError):
        mod._write(ROOT / "research_artifacts/openset_temporal_records.json", {"records": []})
    assert (ROOT / "research_artifacts/openset_temporal_records.json").read_bytes() == before


# --------------------------------------------------------------------------- score dumps
def _synthetic(seed: int = 0, n_benign: int = 1500, n_attack: int = 250) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    d = 8
    parts = [pd.DataFrame(rng.normal(0, 1, (n_benign, d)), columns=[f"f{i}" for i in range(d)]).assign(family="BENIGN")]
    for j, fam in enumerate(["DoS", "PortScan", "Bot"]):
        X = rng.normal(0, 1, (n_attack, d))
        X[:, j] += 4.0
        parts.append(pd.DataFrame(X, columns=[f"f{i}" for i in range(d)]).assign(family=fam))
    df = pd.concat(parts, ignore_index=True)
    df[[f"f{i}" for i in range(d)]] = df[[f"f{i}" for i in range(d)]].astype(np.float32)
    df["day"] = "Monday"
    df["seq"] = np.arange(len(df))
    df["fine_label"] = df["family"]
    df["dataset"] = "synthetic"
    df["is_attack"] = (df["family"] != "BENIGN").astype(np.int8)
    for c in ("day", "fine_label", "family", "dataset"):
        df[c] = df[c].astype("category")
    return df


def _run(dump=None):
    import research.protocols as P
    from research.data import stratified_split
    df = _synthetic()
    tr, va, te = stratified_split(df, (0.6, 0.2, 0.2), 3)
    held = "Bot"
    warm = te[te["family"] == "BENIGN"].iloc[:120]
    test = te.drop(index=warm.index)
    rec = P.run_once(protocol="unit", fold=held, seed=3, train=tr[tr["family"] != held], val=va[va["family"] != held],
                     test=test.reset_index(drop=True), unknown_families=[held], log=lambda m: None,
                     ae_kwargs={"epochs": 2}, warmup=warm, windows=(60, 120), dump=dump)
    return json.loads(json.dumps(rec, default=float))


def test_dump_is_passive_and_complete(tmp_path):
    from research.scoredump import ScoreDump
    plain = _run()
    dump = ScoreDump(tmp_path)
    dumped = _run(dump)
    for k in ("fit_seconds", "score_ms_per_1k_flows"):
        plain.pop(k), dumped.pop(k)
    assert plain == dumped, "enabling the score dump changed the experiment record"

    man = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["files"]
    variants = {e["variant"] for e in man.values()}
    assert variants == {"none", *plain["adaptation"]}
    n_eval = sum(plain["n_test"].values())
    for rel, e in man.items():
        df = pd.read_parquet(tmp_path / rel)
        assert len(df) == n_eval and e["groups"] == plain["n_test"]
        for c in ("raw_sup", "raw_knn", "t_sup", "t_knn", "fused__Aegis-OSR", "p__Aegis-OSR"):
            assert np.isfinite(df[c].to_numpy()).all(), (rel, c)
