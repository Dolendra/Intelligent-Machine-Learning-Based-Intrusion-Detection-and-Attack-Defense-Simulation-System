"""Aegis-OSR: conformal evidence fusion for open-set (zero-day) intrusion detection.

Pipeline for a flow ``x`` (all calibration uses *benign validation* flows never used in fit):

1. Evidence scores     s_sup(x) = 1 - P(BENIGN | x) from a (K+1)-class classifier trained on
                       benign + K known attack families;
                       s_nov(x) = mean distance to the k nearest *benign* training flows.
2. Benign surprisal   t_j(x) = −log P̂_benign(S_j ≥ s_j(x)) from benign split C1, with an
                       exponential tail beyond the largest benign score (``BenignCDF``).
3. Fisher fusion       f(x) = Σ_j t_j(x)  — accumulates evidence, so a flow that
                       is moderately suspicious to *both* the classifier and the novelty
                       detector is ranked above one that is only mildly odd to either.
4. Conformal p-value   p(x) = (1 + #{z ∈ C2 : f(z) ≥ f(x)}) / (|C2| + 1) on a disjoint benign
                       split C2  ⇒  P_benign(p ≤ α) ≤ α in finite samples (exchangeability).
5. Alert               p(x) ≤ α.
6. Attribution         alert and classifier P(attack) ≥ 0.5 → most likely known
                       family k̂ unless its class-conditional (Mondrian) conformal p-value
                       ≤ α_fam → UNKNOWN-ATTACK; alert raised by novelty only → ZERO-DAY-ANOMALY.

The design (Fisher fusion + kNN novelty) was selected on a pilot run (seed 0); reported
results use fresh seeds. Every baseline goes through the *same* steps 2–5 with its own
evidence, so differences come from the evidence and fusion rule, not from calibration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.special import logsumexp
from sklearn.neighbors import NearestNeighbors
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from research.conformal import ConformalCalibrator, MondrianCalibrator
from research.novelty import AutoencoderDetector, IsolationForestDetector

BENIGN = "BENIGN"
UNKNOWN_ATTACK = "UNKNOWN-ATTACK"
ZERO_DAY = "ZERO-DAY-ANOMALY"
PROPOSED = "Aegis-OSR"
NOVELTY_KEY = "knn"


@dataclass(frozen=True)
class MethodSpec:
    evidence: tuple[str, ...]
    fusion: str = "fisher"   # "fisher" | "max" | "omnibus"
    group: str = "baseline"  # "baseline" | "proposed" | "ablation"


METHODS: dict[str, MethodSpec] = {
    # supervised / unsupervised single-evidence baselines
    "Closed-set XGB": MethodSpec(("sup",)),
    "Closed-set DT (v1.1-style)": MethodSpec(("dt",)),
    "Isolation Forest": MethodSpec(("if",)),
    "Autoencoder": MethodSpec(("ae",)),
    "kNN distance": MethodSpec(("knn",)),
    # classifier + its own OOD score (energy, Liu et al. 2020)
    "XGB + Energy": MethodSpec(("sup", "energy"), "max"),
    # proposed + ablations (each changes exactly one design choice)
    PROPOSED: MethodSpec(("sup", "knn"), "fisher", "proposed"),
    "Aegis-OSR w/ max fusion": MethodSpec(("sup", "knn"), "max", "ablation"),
    "Aegis-OSR w/ omnibus fusion": MethodSpec(("sup", "knn"), "omnibus", "ablation"),
    "Aegis-OSR w/ AE novelty": MethodSpec(("sup", "ae"), "fisher", "ablation"),
    "Aegis-OSR w/ IForest novelty": MethodSpec(("sup", "if"), "fisher", "ablation"),
}


def _balanced_weights(y: np.ndarray, power: float = 0.5) -> np.ndarray:
    """Inverse-frequency^power sample weights (sqrt-balancing keeps benign precision)."""
    classes, counts = np.unique(y, return_counts=True)
    lut = dict(zip(classes, (counts.max() / counts) ** power))
    return np.array([lut[v] for v in y], dtype=np.float32)


def build_classifier(n_classes: int, seed: int) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=250, max_depth=8, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8,
        tree_method="hist", objective="multi:softprob", num_class=n_classes,
        eval_metric="mlogloss", n_jobs=-1, random_state=seed,
    )


class BenignCDF:
    """Benign *surprisal* of a score: ``-log P_benign(S >= s)``.

    Inside the benign reference range this is the empirical upper-tail probability
    ``(#{ref >= s} + 1) / (n + 1)`` (never 0). Beyond the largest benign score the tail is
    extrapolated exponentially (peaks-over-threshold): surprisal keeps growing linearly with
    the excess over the maximum, scaled by the mean excess of the top 1% of benign scores.
    The map is continuous and non-decreasing, needs no clipping, and keeps flows far outside
    the benign range ordered — which matters for both AUROC and small calibration windows.
    """

    def __init__(self, ref: np.ndarray) -> None:
        ref = np.sort(np.asarray(ref, dtype=np.float64))
        self.ref = ref
        q99 = np.quantile(ref, 0.99)
        excess = ref[ref > q99] - q99
        spread = float(np.quantile(ref, 0.75) - np.quantile(ref, 0.25))
        self.tail_scale = float(excess.mean()) if excess.size and excess.mean() > 0 else max(spread, 1e-6)

    def surprisal(self, s: np.ndarray) -> np.ndarray:
        s = np.asarray(s, dtype=np.float64)
        n = len(self.ref)
        n_ge = n - np.searchsorted(self.ref, s, side="left")
        out = -np.log((n_ge + 1.0) / (n + 1.0))
        beyond = s > self.ref[-1]
        if beyond.any():
            out[beyond] += (s[beyond] - self.ref[-1]) / self.tail_scale
        return out

    __call__ = surprisal

    def to_dict(self, max_points: int = 20_000) -> dict:
        ref = self.ref
        if len(ref) > max_points:  # quantile sketch, keeps the exact maximum
            ref = np.quantile(ref, np.linspace(0, 1, max_points))
        return {"ref": ref.tolist(), "tail_scale": self.tail_scale}

    @classmethod
    def from_dict(cls, d: dict) -> "BenignCDF":
        obj = cls.__new__(cls)
        obj.ref, obj.tail_scale = np.asarray(d["ref"], dtype=np.float64), float(d["tail_scale"])
        return obj


def fuse(surprisals: list[np.ndarray], rule: str, sum_map: "BenignCDF | None" = None) -> np.ndarray:
    """Combine per-detector benign surprisals into one statistic (higher = more alarming).

    ``max``      largest single surprisal — one strong detector suffices.
    ``fisher``   sum of surprisals — evidence accumulates, but a flow that is extreme for only
                 one detector can fall below the (heavier-tailed) null of the sum.
    ``omnibus``  max(t_1, …, t_m, T(Σ t_j)) where T is the benign surprisal of the Fisher sum:
                 alerts when *any* detector alone **or** their joint evidence is extreme
                 (a min-p / omnibus combination). Conformal calibration of the result keeps
                 the FPR guarantee; the price is ≈ log(m+1) nats of surprisal per test.
    """
    if len(surprisals) == 1 or rule == "max":
        return np.maximum.reduce(surprisals)
    if rule == "fisher":
        return np.sum(surprisals, axis=0)
    if rule == "omnibus":
        if sum_map is None:
            raise ValueError("omnibus fusion needs a benign surprisal map for the Fisher sum")
        return np.maximum.reduce([*surprisals, sum_map(np.sum(surprisals, axis=0))])
    raise ValueError(f"unknown fusion rule {rule!r}")


def _sum_key(spec: "MethodSpec") -> str:
    return "sum:" + "+".join(spec.evidence)


@dataclass
class OSRScores:
    raw: dict[str, np.ndarray]       # evidence scores per flow
    fused: dict[str, np.ndarray]     # fused score per method
    pvalue: dict[str, np.ndarray]    # conformal p-value per method
    proba: np.ndarray                # (n, K+1) class probabilities
    p_fam: np.ndarray                # Mondrian p-value of the predicted attack family
    pred_family_idx: np.ndarray
    extras: dict = field(default_factory=dict)


class AegisOSR:
    """Hybrid open-set detector plus the baselines/ablations it is evaluated against."""

    def __init__(self, seed: int = 0, alpha: float = 0.01, alpha_family: float = 0.01,
                 ae_kwargs: dict | None = None, with_baselines: bool = True, knn_ref: int = 40_000,
                 knn_k: int = 5, clf_factory: Callable[[int, int], object] | None = None,
                 methods: dict[str, MethodSpec] | None = None) -> None:
        self.seed = seed
        self.alpha = alpha
        self.alpha_family = alpha_family
        self.ae_kwargs = {"epochs": 25, **(ae_kwargs or {})}
        self.with_baselines = with_baselines
        self.knn_ref = knn_ref
        self.knn_k = knn_k
        self.classes_: list[str] = []
        # R3: the supervised evidence model and the method set can be swapped; the defaults reproduce v3 exactly
        self.clf_factory = clf_factory
        self.methods = methods if methods is not None else (METHODS if with_baselines else {PROPOSED: METHODS[PROPOSED]})

    # ------------------------------------------------------------------ evidence
    def _needed(self) -> set[str]:
        return {k for spec in self.methods.values() for k in spec.evidence}

    def _raw_scores(self, X: np.ndarray) -> tuple[dict[str, np.ndarray], np.ndarray]:
        need = self._needed()
        proba = self.clf_.predict_proba(X)
        raw = {"sup": 1.0 - proba[:, 0]}
        if "knn" in need:
            raw["knn"] = self.knn_.kneighbors(X)[0].mean(axis=1)
        if "ae" in need:
            raw["ae"] = self.ae_.score(X)
        if "if" in need:
            raw["if"] = self.if_.score(X)
        if "dt" in need:
            raw["dt"] = self.dt_.predict_proba(X)[:, 1]
        if "energy" in need:
            raw["energy"] = -logsumexp(self.clf_.predict(X, output_margin=True), axis=1)
        return raw, proba

    def _fuse(self, raw: dict[str, np.ndarray], spec: MethodSpec) -> np.ndarray:
        return fuse([self.cdf_[k](raw[k]) for k in spec.evidence], spec.fusion, self.cdf_.get(_sum_key(spec)))

    def _fit_maps(self, raw1: dict[str, np.ndarray]) -> None:
        """Per-detector benign surprisal maps (+ maps for omnibus Fisher sums) from split C1."""
        self.cdf_ = {k: BenignCDF(v) for k, v in raw1.items()}
        for spec in self.methods.values():
            if spec.fusion == "omnibus" and len(spec.evidence) > 1:
                total = np.sum([self.cdf_[k](raw1[k]) for k in spec.evidence], axis=0)
                self.cdf_[_sum_key(spec)] = BenignCDF(total)

    # ------------------------------------------------------------------ fit
    def fit(self, X_train: np.ndarray, fam_train: np.ndarray, X_val: np.ndarray, fam_val: np.ndarray,
            log: Callable[[str], None] = lambda m: None) -> "AegisOSR":
        rng = np.random.default_rng(self.seed)
        fam_train = np.asarray(fam_train).astype(str)
        fam_val = np.asarray(fam_val).astype(str)
        self.classes_ = [BENIGN] + sorted(c for c in set(fam_train) if c != BENIGN)
        lut = {c: i for i, c in enumerate(self.classes_)}
        y = np.array([lut[c] for c in fam_train])
        need = self._needed()

        log(f"classifier: {'XGB' if self.clf_factory is None else 'custom'} over {self.classes_}")
        self.clf_ = (self.clf_factory or build_classifier)(len(self.classes_), self.seed)
        self.clf_.fit(X_train, y, sample_weight=_balanced_weights(y))

        benign_tr = X_train[y == 0]
        ref = benign_tr[rng.choice(len(benign_tr), min(self.knn_ref, len(benign_tr)), replace=False)]
        self.knn_ref_X_ = ref
        self.knn_ = NearestNeighbors(n_neighbors=self.knn_k, algorithm="brute", n_jobs=-1).fit(ref)
        if "ae" in need:
            log(f"autoencoder on {len(benign_tr):,} benign flows")
            self.ae_ = AutoencoderDetector(seed=self.seed, **self.ae_kwargs).fit(benign_tr)
        if "if" in need:
            self.if_ = IsolationForestDetector(seed=self.seed).fit(benign_tr)
        if "dt" in need:
            self.dt_ = DecisionTreeClassifier(max_depth=20, class_weight="balanced", random_state=self.seed)
            self.dt_.fit(X_train, (y != 0).astype(int))

        # ---- benign calibration: C1 → per-score CDFs, C2 → conformal on fused score
        vb_idx = rng.permutation(np.flatnonzero(fam_val == BENIGN))
        c1, c2 = vb_idx[: len(vb_idx) // 2], vb_idx[len(vb_idx) // 2:]
        raw1, _ = self._raw_scores(X_val[c1])
        raw2, _ = self._raw_scores(X_val[c2])
        self._fit_maps(raw1)
        self.cal_ = {m: ConformalCalibrator().fit(self._fuse(raw2, spec)) for m, spec in self.methods.items()}
        self.n_cal_ = (len(c1), len(c2))

        # ---- Mondrian calibration: nonconformity of known attacks w.r.t. their true family
        va = (fam_val != BENIGN) & np.isin(fam_val, self.classes_)
        self.cal_fam_ = MondrianCalibrator()
        if va.any():
            yv = np.array([lut[c] for c in fam_val[va]])
            pv = self.clf_.predict_proba(X_val[va])
            ap = pv[:, 1:] / np.maximum(pv[:, 1:].sum(axis=1, keepdims=True), 1e-12)
            self.cal_fam_.fit(1.0 - ap[np.arange(len(yv)), yv - 1], yv)
        return self

    # ------------------------------------------------------------------ adapt
    _STATE = ("cdf_", "cal_", "knn_", "knn_ref_X_", "n_cal_")

    def snapshot(self) -> dict:
        return {k: getattr(self, k) for k in self._STATE}

    def restore(self, state: dict) -> "AegisOSR":
        for k, v in state.items():
            setattr(self, k, v)
        return self

    def recalibrate(self, X_benign: np.ndarray, *, update_reference: bool = False) -> "AegisOSR":
        """Label-light adaptation to a new environment **without retraining**.

        ``X_benign`` is a small window of target-environment flows confirmed benign (e.g. the
        first minutes of a new capture day). The benign CDFs (C1) and conformal calibration
        (C2) are re-estimated on it, restoring the FPR guarantee for flows exchangeable with
        the window. With ``update_reference`` one third of the window is first appended to the
        kNN benign reference, so the novelty detector itself learns the new benign modes;
        those flows are then excluded from calibration to avoid zero self-distances.
        """
        rng = np.random.default_rng(self.seed + 7919)
        idx = rng.permutation(len(X_benign))
        if update_reference:
            n_ref = len(idx) // 3
            ref_new, idx = X_benign[idx[:n_ref]], idx[n_ref:]
            self.knn_ref_X_ = np.vstack([self.knn_ref_X_, ref_new])
            self.knn_ = NearestNeighbors(n_neighbors=self.knn_k, algorithm="brute", n_jobs=-1).fit(self.knn_ref_X_)
        c1, c2 = idx[: len(idx) // 2], idx[len(idx) // 2:]
        raw1, _ = self._raw_scores(X_benign[c1])
        raw2, _ = self._raw_scores(X_benign[c2])
        self._fit_maps(raw1)
        self.cal_ = {m: ConformalCalibrator().fit(self._fuse(raw2, spec)) for m, spec in self.methods.items()}
        self.n_cal_ = (len(c1), len(c2))
        return self

    # ------------------------------------------------------------------ score
    def score(self, X: np.ndarray) -> OSRScores:
        raw, proba = self._raw_scores(X)
        fused = {m: self._fuse(raw, spec) for m, spec in self.methods.items()}
        pval = {m: self.cal_[m].pvalue(f) for m, f in fused.items()}
        ap = proba[:, 1:] / np.maximum(proba[:, 1:].sum(axis=1, keepdims=True), 1e-12)
        fam_idx = ap.argmax(axis=1) + 1
        p_fam = self.cal_fam_.pvalue(1.0 - ap.max(axis=1), fam_idx)
        return OSRScores(raw=raw, fused=fused, pvalue=pval, proba=proba, p_fam=p_fam, pred_family_idx=fam_idx)

    # ------------------------------------------------------------------ decide
    def label(self, sc: OSRScores, alpha: float | None = None) -> np.ndarray:
        """Open-set labels under the proposed Aegis-OSR rule."""
        a = self.alpha if alpha is None else alpha
        alert = sc.pvalue[PROPOSED] <= a
        supervised = alert & (sc.raw["sup"] >= 0.5)  # classifier itself calls it an attack
        known = supervised & (sc.p_fam > self.alpha_family)
        names = np.array(self.classes_, dtype=object)
        out = np.full(len(alert), BENIGN, dtype=object)
        out[alert] = ZERO_DAY
        out[supervised] = UNKNOWN_ATTACK
        out[known] = names[sc.pred_family_idx[known]]
        return out


def method_scores(sc: OSRScores) -> dict[str, dict]:
    """Per method: continuous ``score`` (for AUROC) and conformal ``pvalue`` (for alerts)."""
    return {m: {"score": sc.fused[m], "pvalue": sc.pvalue[m]} for m in sc.fused}
