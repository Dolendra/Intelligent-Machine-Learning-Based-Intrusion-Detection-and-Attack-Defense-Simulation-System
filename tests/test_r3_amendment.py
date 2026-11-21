"""R3 amendment (Phase 4): PR-01 smoothed p-values, PR-02 frozen configs, PR-03 unified methods /
feature-only hashes, PR-04 cross-dataset LOAFO, and the staleness screen used by the reliability study."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research.conformal import ConformalCalibrator
from research.openset import BENIGN, PROPOSED, AegisOSR

ROOT = Path(__file__).resolve().parents[1]


def _runner():
    spec = importlib.util.spec_from_file_location("r3run", ROOT / "scripts" / "67_r3_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ----------------------------------------------------------------------------- PR-01
def test_smoothed_pvalue_is_exact_under_heavy_ties_where_deterministic_is_not():
    rng = np.random.default_rng(0)
    levels = np.array([0.0, 0.1, 0.5, 0.9, 1.0])
    probs = np.array([0.6, 0.2, 0.15, 0.04, 0.01])          # a decision tree's few distinct leaf values
    cal = rng.choice(levels, 20_000, p=probs)
    test = rng.choice(levels, 200_000, p=probs)              # exchangeable benign test flows
    c = ConformalCalibrator().fit(cal)
    det = c.pvalue(test)
    smo = c.pvalue_smoothed(test, np.random.default_rng(1))
    for alpha in (0.005, 0.01, 0.05):
        assert abs((smo <= alpha).mean() - alpha) < 0.15 * alpha + 5e-4   # exact up to sampling error
    assert abs((det <= 0.01).mean() - 0.01) > 0.005                       # ties: the deterministic rule is off
    assert np.all(smo <= det + 1e-12)


def test_smoothed_pvalue_matches_deterministic_without_ties_up_to_one_rank():
    rng = np.random.default_rng(3)
    c = ConformalCalibrator().fit(rng.normal(size=999))
    s = rng.normal(size=5000)
    det, smo = c.pvalue(s), c.pvalue_smoothed(s, np.random.default_rng(4))
    assert np.all(det - smo <= 1.0 / 1000 + 1e-12) and np.all(smo <= det + 1e-12)


def _fit_small(pvalue_mode):
    rng = np.random.default_rng(0)
    X = np.r_[rng.normal(0, 1, (2000, 4)), rng.normal(4, 0.5, (300, 4))]
    y = np.array([BENIGN] * 2000 + ["A"] * 300)
    Xv = np.r_[rng.normal(0, 1, (2000, 4)), rng.normal(4, 0.5, (100, 4))]
    yv = np.array([BENIGN] * 2000 + ["A"] * 100)
    from sklearn.tree import DecisionTreeClassifier
    return AegisOSR(seed=0, with_baselines=False, knn_ref=1000, pvalue_mode=pvalue_mode,
                    clf_factory=lambda k, s: DecisionTreeClassifier(random_state=s, max_depth=4)).fit(X, y, Xv, yv), rng


def test_aegis_osr_default_is_deterministic_and_smoothed_keeps_both_rules():
    m_det, rng = _fit_small("deterministic")
    m_smo, _ = _fit_small("smoothed")
    Xt = rng.normal(0, 1, (3000, 4))
    sd, ss = m_det.score(Xt), m_smo.score(Xt)
    assert sd.pvalue_det is None
    np.testing.assert_allclose(ss.pvalue_det[PROPOSED], sd.pvalue[PROPOSED])   # deterministic kept as sensitivity
    assert np.all(ss.pvalue[PROPOSED] <= ss.pvalue_det[PROPOSED] + 1e-12)
    # reproducible: same seed, same call order -> same draws
    m2, _ = _fit_small("smoothed")
    np.testing.assert_array_equal(m2.score(Xt).pvalue[PROPOSED], ss.pvalue[PROPOSED])
    with pytest.raises(ValueError):
        AegisOSR(pvalue_mode="random")


# ----------------------------------------------------------------------------- screen (reliability study)
def test_stream_screen_is_near_alpha0_without_shift_and_high_under_shift():
    from research.protocols import stream_screen
    m, rng = _fit_small("deterministic")
    same = stream_screen(m, rng.normal(0, 1, (500, 4)))
    shifted = stream_screen(m, rng.normal(0, 1, (500, 4)) + 3.0)
    assert same["window"] == 500 and abs(same["exceedance"]["knn"] - 0.05) < 0.04
    assert shifted["exceedance"]["knn"] > 0.5
    assert stream_screen(m, np.empty((0, 4))) == {}


# ----------------------------------------------------------------------------- PR-02
def test_campaign_refuses_without_frozen_configs(tmp_path, monkeypatch):
    R = _runner()
    monkeypatch.setattr(R, "FROZEN_CONFIGS", tmp_path / "missing.json")
    with pytest.raises(SystemExit) as e:
        R.load_frozen_configs()
    assert "frozen" in str(e.value)


def test_frozen_configs_file_matches_amended_design_and_is_never_overwritten():
    path = ROOT / "research_artifacts" / "r3" / "configs" / "frozen_configs.json"
    if not path.exists():
        pytest.skip("configs not frozen yet")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    assert cfg["design"]["seeds"] == [101, 102, 103, 104, 105]
    assert cfg["design"]["pvalue_mode"] == "smoothed"
    assert cfg["tuning"]["trials_per_model"] == 0
    assert set(cfg["models"]) == {"xgb_ref", "dt", "rf", "et", "xgb", "lgbm", "catboost"}
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "73_freeze_r3_configs.py")], capture_output=True,
                       text=True, cwd=ROOT)
    assert r.returncode != 0 and "never overwritten" in (r.stdout + r.stderr)


# ----------------------------------------------------------------------------- PR-03
def test_unified_model_kwargs_give_every_model_the_same_method_names():
    R = _runner()
    names = {m: set(R.model_kwargs(m, unified=True)["methods"]) for m in ("xgb_ref", "dt", "rf")}
    assert names["xgb_ref"] == names["dt"] == names["rf"] == set(R.R3_METHODS)
    assert R.model_kwargs("xgb_ref")["methods"] is R.METHODS            # regression-gated path unchanged
    assert R.model_kwargs("dt", unified=True, pvalue_mode="smoothed")["pvalue_mode"] == "smoothed"


def test_feature_only_overlap_is_reported_not_fatal():
    R = _runner()
    chk = R.LeakageChecker()
    tr = pd.DataFrame({"a": np.float32([1, 3]), "b": np.float32([2, 4]), "family": ["BENIGN", "DoS"],
                       "fine_label": ["BENIGN", "DoS"]})
    te = pd.DataFrame({"a": np.float32([3, 9]), "b": np.float32([4, 9]), "family": ["BENIGN", "BENIGN"],
                       "fine_label": ["BENIGN", "BENIGN"]})   # same features as a train DoS row, other label
    chk({"protocol": "loafo", "fold": "x", "seed": 0, "unknown": []}, {"train": tr, "val": None, "test": te})
    assert chk.log[-1]["pass"] and chk.log[-1]["feature_only_overlaps"]["train&test"] == 1


# ----------------------------------------------------------------------------- PR-04
def _toy_datasets():
    rng = np.random.default_rng(5)
    feats = [f"f{i}" for i in range(4)]

    def block(n, centre, fam, day, ds):
        df = pd.DataFrame(rng.normal(centre, 0.6, (n, 4)).astype(np.float32), columns=feats)
        df["fine_label"], df["family"], df["day"], df["dataset"] = fam, fam, day, ds
        return df

    src = pd.concat([block(6000, 0, "BENIGN", "Monday", "a"), block(800, 4, "DoS", "Wednesday", "a"),
                     block(800, -4, "Bot", "Friday", "a"), block(800, 8, "PortScan", "Friday", "a")],
                    ignore_index=True)
    dst = pd.concat([block(3000, 0.2, "BENIGN", "d1", "b"), block(400, 4, "DoS", "d1", "b"),
                     block(3000, 0.2, "BENIGN", "d2", "b"), block(400, -4, "Bot", "d2", "b")], ignore_index=True)
    for df in (src, dst):
        df["seq"] = np.arange(len(df))
        df["is_attack"] = df["family"] != "BENIGN"
    return src, dst


def test_cross_loafo_holds_family_out_of_every_source_split_and_scores_it_as_unknown(monkeypatch):
    import research.protocols as P
    monkeypatch.setattr(P, "TRAIN_CAPS", {"BENIGN": 3000, "_attack": 500})
    monkeypatch.setattr(P, "VAL_CAPS", {"BENIGN": 2400, "_attack": 200})
    monkeypatch.setattr(P, "PERDAY_TEST_CAPS", {"BENIGN": 800, "_attack": 300})
    from sklearn.tree import DecisionTreeClassifier
    seen = []
    src, dst = _toy_datasets()
    recs = P.cross_loafo(
        src, dst, seeds=[0], windows=(600,), log=lambda m: None, on_split=lambda k, s: seen.append((k, s)),
        model_kwargs={"with_baselines": False, "knn_ref": 1000, "pvalue_mode": "smoothed",
                      "clf_factory": lambda k, s: DecisionTreeClassifier(random_state=s, max_depth=4)})
    assert {r["held_out"] for r in recs} == {"Bot", "DoS"}
    for key, splits in seen:
        held = key["unknown"][0]
        assert key["protocol"] == "cross_loafo"
        assert (splits["train"]["family"] == held).sum() == 0 and (splits["val"]["family"] == held).sum() == 0
    for r in recs:
        assert r["unknown_families"] == [r["held_out"]] and r["fold"].startswith(r["held_out"] + "@")
        assert r["warmup_eval_overlap"] == 0 and "knn" in r["screen"]["exceedance"]
        assert "recal@600" in r["adaptation"]
