"""Serving-side Aegis-OSR "Zero-Day Gate".

Loads the artifacts written by ``scripts/51_train_zero_day_gate.py`` and scores flows with
the exact decision rule evaluated in the research protocols (Fisher fusion of supervised and
kNN-novelty benign surprisals, conformal FPR control, Mondrian family conformity).

It is **advisory**: it runs beside the frozen v1.1 detector and never changes that model's
verdict. Its job is to surface flows that the closed-set model cannot recognize.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from xgboost import XGBClassifier

from ids_config import ROOT
from research.conformal import ConformalCalibrator, MondrianCalibrator
from research.features import SignedLogScaler
from research.openset import BENIGN, UNKNOWN_ATTACK, ZERO_DAY, BenignCDF, fuse

GATE_DIR = ROOT / "models" / "trained_models" / "aegis_osr"
BUNDLE = "aegis_osr_bundle.joblib"
CLASSIFIER = "aegis_osr_classifier.ubj"
METADATA = "aegis_osr_metadata.json"

LABEL_TEXT = {
    BENIGN: "Consistent with benign traffic",
    UNKNOWN_ATTACK: "Attack-like, but does not conform to any known family",
    ZERO_DAY: "Novel behaviour — unlike benign traffic and not recognized as a known attack",
}


def export_gate(model, scaler: SignedLogScaler, features: list[str], out_dir: Path, metadata: dict) -> dict:
    """Serialize a fitted ``AegisOSR`` (with_baselines=False) for serving."""
    from research.openset import PROPOSED

    out_dir.mkdir(parents=True, exist_ok=True)
    model.clf_.save_model(out_dir / CLASSIFIER)
    bundle = {
        "features": list(features),
        "classes": list(model.classes_),
        "alpha": model.alpha,
        "alpha_family": model.alpha_family,
        "knn_k": model.knn_k,
        "scaler": scaler.to_dict(),
        "cdf": {k: v.to_dict() for k, v in model.cdf_.items()},
        "conformal": model.cal_[PROPOSED].to_dict(max_points=50_000),
        "mondrian": {int(c): cal.to_dict() for c, cal in model.cal_fam_.cals_.items()},
        "knn_reference": np.asarray(model.knn_ref_X_, dtype=np.float32),
    }
    joblib.dump(bundle, out_dir / BUNDLE, compress=3)
    (out_dir / METADATA).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {p.name: p.stat().st_size for p in out_dir.iterdir()}


class ZeroDayGate:
    def __init__(self, directory: Path = GATE_DIR) -> None:
        b = joblib.load(directory / BUNDLE)
        self.metadata: dict = json.loads((directory / METADATA).read_text(encoding="utf-8"))
        self.features: list[str] = b["features"]
        self.classes: list[str] = b["classes"]
        self.alpha: float = float(b["alpha"])
        self.alpha_family: float = float(b["alpha_family"])
        self.scaler = SignedLogScaler.from_dict(b["scaler"])
        self.cdf = {k: BenignCDF.from_dict(v) for k, v in b["cdf"].items()}
        self.cal = ConformalCalibrator.from_dict(b["conformal"])
        self.mondrian = MondrianCalibrator()
        self.mondrian.cals_ = {int(c): ConformalCalibrator.from_dict(d) for c, d in b["mondrian"].items()}
        self.ref = b["knn_reference"]
        self.knn = NearestNeighbors(n_neighbors=int(b["knn_k"]), algorithm="brute").fit(self.ref)
        self.clf = XGBClassifier()
        self.clf.load_model(directory / CLASSIFIER)
        self.clf.set_params(n_jobs=4)
        import hashlib

        digest = hashlib.sha256((directory / BUNDLE).read_bytes()).hexdigest()[:12]
        self.version = f"aegis-osr@{digest}"

    # ------------------------------------------------------------------ helpers
    def _frame(self, rows: pd.DataFrame | list[dict[str, Any]]) -> np.ndarray:
        df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
        missing = [f for f in self.features if f not in df.columns]
        if missing:
            raise ValueError(f"Zero-day gate: missing {len(missing)} features, e.g. {missing[:3]}")
        X = df[self.features].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        return self.scaler.transform(X)

    def _deviations(self, z: np.ndarray, neighbor_idx: np.ndarray, top: int) -> list[dict]:
        nb = self.ref[neighbor_idx].mean(axis=0)
        diff = z - nb
        order = np.argsort(-np.abs(diff))[:top]
        raw_flow = self.scaler.inverse_transform(z[None, :])[0]
        raw_nb = self.scaler.inverse_transform(nb[None, :])[0]
        return [
            {
                "feature": self.features[i],
                "value": float(raw_flow[i]),
                "benign_neighbor_value": float(raw_nb[i]),
                "deviation_sigma": float(diff[i]),
            }
            for i in order
        ]

    # ------------------------------------------------------------------ public
    def assess(self, rows: pd.DataFrame | list[dict[str, Any]], *, explain_top: int = 5,
               alpha: float | None = None) -> list[dict[str, Any]]:
        a = self.alpha if alpha is None else float(alpha)
        Z = self._frame(rows)
        proba = self.clf.predict_proba(Z)
        s_sup = 1.0 - proba[:, 0]
        dist, idx = self.knn.kneighbors(Z)
        s_knn = dist.mean(axis=1)
        t_sup, t_knn = self.cdf["sup"](s_sup), self.cdf["knn"](s_knn)
        fused = fuse([t_sup, t_knn], "fisher")
        pval = self.cal.pvalue(fused)
        ap = proba[:, 1:] / np.maximum(proba[:, 1:].sum(axis=1, keepdims=True), 1e-12)
        fam_idx = ap.argmax(axis=1) + 1
        p_fam = self.mondrian.pvalue(1.0 - ap.max(axis=1), fam_idx)

        out = []
        for i in range(len(Z)):
            alert = bool(pval[i] <= a)
            supervised = alert and s_sup[i] >= 0.5
            if not alert:
                label = BENIGN
            elif supervised and p_fam[i] > self.alpha_family:
                label = self.classes[fam_idx[i]]
            elif supervised:
                label = UNKNOWN_ATTACK
            else:
                label = ZERO_DAY
            novel = label in (UNKNOWN_ATTACK, ZERO_DAY)
            out.append({
                "label": label,
                "alert": alert,
                "novel": novel,
                "summary": LABEL_TEXT.get(label, f"Matches known family: {label}"),
                "p_value": float(pval[i]),
                "alpha": a,
                "fused_surprisal": float(fused[i]),
                "evidence": {
                    "supervised": {"p_attack": float(s_sup[i]), "surprisal": float(t_sup[i])},
                    "novelty": {"knn_distance": float(s_knn[i]), "surprisal": float(t_knn[i])},
                },
                "family": {
                    "predicted": self.classes[fam_idx[i]],
                    "probability": float(ap[i].max()),
                    "conformity_p": float(p_fam[i]),
                },
                "top_deviations": self._deviations(Z[i], idx[i], explain_top) if (explain_top and alert) else [],
            })
        return out

    def status(self) -> dict[str, Any]:
        return {
            "available": True,
            "version": self.version,
            "alpha": self.alpha,
            "alpha_family": self.alpha_family,
            "known_classes": self.classes,
            "n_features": len(self.features),
            "knn_reference_size": int(len(self.ref)),
            "calibration_size": self.cal.n,
            **{k: self.metadata.get(k) for k in ("trained_at", "git_commit", "training", "evaluation", "method")},
        }


_gate: ZeroDayGate | None = None
_gate_error: str | None = None
_gate_error_at: float = 0.0
_lock = threading.Lock()
RETRY_SECONDS = 60.0  # R-04 (ARCH-10): a failed load is retried, not remembered forever


def get_gate() -> ZeroDayGate | None:
    """Lazy singleton; returns None (and remembers why) when artifacts are missing.

    A failed load is retried after ``RETRY_SECONDS``, so gate artifacts restored after
    startup are picked up without a restart.
    """
    global _gate, _gate_error, _gate_error_at
    if _gate is not None:
        return _gate
    if _gate_error is not None and (time.monotonic() - _gate_error_at) < RETRY_SECONDS:
        return None
    with _lock:
        if _gate is None:
            try:
                _gate = ZeroDayGate()
                _gate_error = None
            except FileNotFoundError:
                _gate_error = "Zero-day gate artifacts not found. Run scripts/51_train_zero_day_gate.py"
                _gate_error_at = time.monotonic()
            except Exception as exc:  # noqa: BLE001
                _gate_error = f"Zero-day gate failed to load: {type(exc).__name__}"
                _gate_error_at = time.monotonic()
    return _gate


def gate_error() -> str | None:
    return _gate_error
