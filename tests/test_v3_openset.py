"""v3 research core: conformal validity, surprisal maps, fusion rules, and Aegis-OSR on synthetic data."""
from __future__ import annotations

import numpy as np
import pytest

from research.conformal import ConformalCalibrator, MondrianCalibrator
from research.features import SignedLogScaler
from research.metrics import mean_ci, paired_test
from research.openset import BENIGN, PROPOSED, UNKNOWN_ATTACK, ZERO_DAY, AegisOSR, BenignCDF, fuse


def test_conformal_pvalues_control_false_positive_rate():
    rng = np.random.default_rng(0)
    fprs = []
    for _ in range(40):
        cal = ConformalCalibrator().fit(rng.normal(size=500))
        p = cal.pvalue(rng.normal(size=5000))
        assert p.min() >= 1 / 501 and p.max() <= 1.0
        fprs.append((p <= 0.05).mean())
    # finite-sample guarantee holds in expectation; the average over draws must respect it
    assert np.mean(fprs) <= 0.05 + 0.005


def test_conformal_threshold_matches_pvalue_rule():
    cal = ConformalCalibrator().fit(np.arange(99, dtype=float))  # n = 99
    thr = cal.threshold(0.05)  # k = floor(0.05 * 100) - 1 = 4 → flag iff s > 5th-largest score (94)
    assert thr == 94.0
    assert cal.pvalue(np.array([94.5]))[0] <= 0.05 < cal.pvalue(np.array([94.0]))[0]
    rng = np.random.default_rng(5)
    s = rng.uniform(80, 110, 2000)
    np.testing.assert_array_equal(cal.pvalue(s) <= 0.05, s > thr)


def test_mondrian_vetoes_nonconforming_class_only():
    rng = np.random.default_rng(1)
    nonconf = np.r_[rng.uniform(0, 0.1, 200), rng.uniform(0, 0.1, 200)]
    classes = np.r_[np.ones(200, int), np.full(200, 2)]
    m = MondrianCalibrator().fit(nonconf, classes)
    p = m.pvalue(np.array([0.05, 0.9, 0.9]), np.array([1, 1, 7]))
    assert p[0] > 0.1 and p[1] < 0.01
    assert p[2] == 1.0  # uncalibrated class → no veto


def test_benign_surprisal_is_monotone_and_extrapolates():
    rng = np.random.default_rng(2)
    cdf = BenignCDF(rng.exponential(size=2000))
    s = np.linspace(-1, 40, 4000)
    t = cdf(s)
    assert np.all(np.diff(t) >= -1e-12)
    top = cdf.ref[-1]
    beyond = cdf(np.array([top, top + 1, top + 10]))
    assert beyond[1] > beyond[0] and beyond[2] > beyond[1]  # no ceiling past the benign max
    restored = BenignCDF.from_dict(cdf.to_dict())
    np.testing.assert_allclose(restored(s), t)


def test_fusion_rules():
    a, b = np.array([1.0, 5.0, 0.0]), np.array([1.0, 0.0, 6.0])
    np.testing.assert_allclose(fuse([a, b], "max"), [1, 5, 6])
    np.testing.assert_allclose(fuse([a, b], "fisher"), [2, 5, 6])
    with pytest.raises(ValueError):
        fuse([a, b], "omnibus")  # needs the Fisher-sum map
    with pytest.raises(ValueError):
        fuse([a, b], "nope")


def test_signed_log_scaler_roundtrip():
    rng = np.random.default_rng(3)
    X = np.c_[rng.normal(0, 1e6, 500), rng.exponential(10, 500), np.zeros(500)]
    sc = SignedLogScaler().fit(X)
    Z = sc.transform(X)
    assert Z.dtype == np.float32 and np.isfinite(Z).all()
    np.testing.assert_allclose(sc.inverse_transform(Z), X, rtol=1e-3, atol=1e-3)


def test_stats_helpers():
    ci = mean_ci([0.5, 0.6, 0.7])
    assert ci["ci_low"] < 0.6 < ci["ci_high"] and ci["n"] == 3
    assert mean_ci([None, float("nan")])["n"] == 0
    t = paired_test([0.9] * 6, [0.5, 0.4, 0.6, 0.5, 0.3, 0.45])
    assert t["wins"] == 6 and t["p_value"] < 0.05


def _synthetic(seed: int, n_benign: int = 3000):
    """Benign blob, two known attack clusters, one never-seen cluster."""
    rng = np.random.default_rng(seed)
    d = 6
    benign = rng.normal(0, 1, (n_benign, d))
    a1 = rng.normal(0, 0.5, (400, d)) + np.r_[5, 0, 0, 0, 0, 0]
    a2 = rng.normal(0, 0.5, (400, d)) + np.r_[0, 5, 0, 0, 0, 0]
    unknown = rng.normal(0, 0.5, (300, d)) + np.r_[0, 0, 0, 0, -6, 6]
    return benign, a1, a2, unknown


def test_aegis_osr_detects_unseen_cluster_with_controlled_fpr():
    benign, a1, a2, unknown = _synthetic(0)
    vb, va1, va2, _ = _synthetic(1)
    tb, ta1, _, tu = _synthetic(2)
    X = np.r_[benign, a1, a2]
    y = np.array([BENIGN] * len(benign) + ["A1"] * len(a1) + ["A2"] * len(a2))
    Xv = np.r_[vb, va1, va2]
    yv = np.array([BENIGN] * len(vb) + ["A1"] * len(va1) + ["A2"] * len(va2))
    model = AegisOSR(seed=0, alpha=0.01, with_baselines=False, knn_ref=2000)
    model.fit(X, y, Xv, yv)
    sc = model.score(np.r_[tb, ta1, tu])
    p = sc.pvalue[PROPOSED]
    nb, nk = len(tb), len(ta1)
    assert (p[:nb] <= 0.01).mean() <= 0.03  # benign FPR near alpha
    assert (p[nb:nb + nk] <= 0.01).mean() > 0.95  # known attacks
    assert (p[nb + nk:] <= 0.01).mean() > 0.9  # never-seen cluster
    labels = model.label(sc)
    assert (labels[nb:nb + nk] == "A1").mean() > 0.9
    assert np.isin(labels[nb + nk:], [ZERO_DAY, UNKNOWN_ATTACK]).mean() > 0.9

    # recalibration API keeps the model usable and snapshot/restore is lossless
    state = model.snapshot()
    model.recalibrate(tb[:600], update_reference=True)
    model.restore(state)
    np.testing.assert_allclose(model.score(tb[:50]).pvalue[PROPOSED], sc.pvalue[PROPOSED][:50])
