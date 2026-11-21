"""Split-conformal calibration of novelty / attack scores.

Given calibration scores ``s_1..s_n`` from benign flows held out from training, the
conformal p-value of a new flow with score ``s`` is

    p(s) = (1 + #{i : s_i >= s}) / (n + 1).

If the new flow is benign and exchangeable with the calibration flows, then
``P(p <= alpha) <= alpha`` for every alpha — i.e. flagging flows with ``p <= alpha`` has a
finite-sample guaranteed benign false-positive rate of at most ``alpha``. Combining two
p-values with a Bonferroni rule (flag if ``min(p1, p2) <= alpha / 2``) preserves the bound.

``MondrianCalibrator`` applies the same idea per predicted class (class-conditional
conformal), which is how Aegis-OSR decides that an alert does *not* conform to any known
attack family ("UNKNOWN-ATTACK").
"""
from __future__ import annotations

import numpy as np


class ConformalCalibrator:
    def __init__(self) -> None:
        self.cal_: np.ndarray | None = None

    def fit(self, cal_scores: np.ndarray) -> "ConformalCalibrator":
        cal = np.asarray(cal_scores, dtype=np.float64)
        if cal.size == 0:
            raise ValueError("Conformal calibration needs at least one score")
        self.cal_ = np.sort(cal)
        return self

    @property
    def n(self) -> int:
        return 0 if self.cal_ is None else int(self.cal_.size)

    def pvalue(self, scores: np.ndarray) -> np.ndarray:
        if self.cal_ is None:
            raise RuntimeError("ConformalCalibrator is not fitted")
        s = np.asarray(scores, dtype=np.float64)
        n_ge = self.n - np.searchsorted(self.cal_, s, side="left")
        return (1.0 + n_ge) / (self.n + 1.0)

    def pvalue_smoothed(self, scores: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        """Randomised (smoothed) conformal p-value (R3 amendment PR-01, RES-2).

            p(s) = (#{i : s_i > s} + U * (1 + #{i : s_i = s})) / (n + 1),   U ~ Uniform(0, 1)

        Under exchangeability ``P(p <= alpha) = alpha`` *exactly* (Vovk et al. 2005), so tied scores
        (e.g. a decision tree's few distinct leaf probabilities) no longer push the realised
        false-alarm rate far below or above alpha. It is always <= the deterministic p-value.
        """
        if self.cal_ is None:
            raise RuntimeError("ConformalCalibrator is not fitted")
        s = np.asarray(scores, dtype=np.float64)
        lo = np.searchsorted(self.cal_, s, side="left")
        hi = np.searchsorted(self.cal_, s, side="right")
        n_gt = self.n - hi
        n_eq = hi - lo
        u = rng.random(s.shape)
        return (n_gt + u * (1.0 + n_eq)) / (self.n + 1.0)

    def threshold(self, alpha: float) -> float:
        """Strict alert boundary: ``pvalue(s) <= alpha`` exactly when ``s > threshold``.

        A flow is flagged when at most ``k = floor(alpha (n+1)) - 1`` calibration scores are
        >= its score, i.e. when it exceeds the (k+1)-th largest calibration score.
        """
        k = int(np.floor(alpha * (self.n + 1))) - 1
        if k < 0:
            return float("inf")
        if k >= self.n:
            return float("-inf")
        return float(self.cal_[self.n - 1 - k])

    def to_dict(self, max_points: int = 20_000) -> dict:
        cal = self.cal_
        if cal.size > max_points:  # quantile sketch keeps the export small
            cal = np.quantile(cal, np.linspace(0, 1, max_points))
        return {"cal": cal.tolist(), "n_original": self.n}

    @classmethod
    def from_dict(cls, d: dict) -> "ConformalCalibrator":
        c = cls()
        c.cal_ = np.asarray(d["cal"], dtype=np.float64)
        return c


class MondrianCalibrator:
    """Class-conditional conformal calibration (one calibrator per class)."""

    def __init__(self, min_count: int = 20) -> None:
        self.min_count = min_count
        self.cals_: dict[int, ConformalCalibrator] = {}

    def fit(self, nonconformity: np.ndarray, classes: np.ndarray) -> "MondrianCalibrator":
        nonconformity = np.asarray(nonconformity)
        classes = np.asarray(classes)
        for c in np.unique(classes):
            vals = nonconformity[classes == c]
            if vals.size >= self.min_count:
                self.cals_[int(c)] = ConformalCalibrator().fit(vals)
        return self

    def pvalue(self, nonconformity: np.ndarray, classes: np.ndarray) -> np.ndarray:
        nonconformity = np.asarray(nonconformity)
        classes = np.asarray(classes)
        p = np.ones(len(classes), dtype=np.float64)  # classes without calibration: no veto
        for c, cal in self.cals_.items():
            m = classes == c
            if m.any():
                p[m] = cal.pvalue(nonconformity[m])
        return p
