"""Detection helpers for the controlled lab (frozen ML preferred; oracle fallback)."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

DetectionMode = Literal["frozen_ml", "label_oracle"]


@dataclass
class DetectionResult:
    detected: bool
    mode: DetectionMode
    attack_type: str
    confidence: float
    latency_s: float
    n_flows_scored: int
    detail: dict[str, Any]


@dataclass
class FrozenDetector:
    """Load frozen DT once; score attack-family samples per call."""

    model_dir: Path
    threshold: float = 0.85
    _bundle: Any = field(default=None, repr=False)
    _binary: Any = field(default=None, repr=False)
    _pool: dict[str, Any] = field(default_factory=dict, repr=False)
    _ready: bool = False
    _error: str | None = None

    def load(self) -> None:
        if self._ready:
            return
        try:
            from ids_config import load_config
            from ml.features.pipeline import FeatureBundle
            from ml.models.factory import load_model
            from ml.preprocessing.dataset import load_processed

            cfg = load_config()
            thr = float(cfg["models"].get("binary_threshold", self.threshold))
            op = self.model_dir / "threshold_operating_point.json"
            if op.exists():
                thr = float(json.loads(op.read_text(encoding="utf-8")).get("operating_threshold", thr))
            self.threshold = thr
            self._bundle = FeatureBundle.load(self.model_dir / "feature_bundle.joblib")
            self._binary = load_model(self.model_dir / "binary_best.joblib")
            try:
                df = load_processed("test")
            except Exception:
                df = load_processed("train")
            self._pool["_all_attack"] = df[df["Label"].astype(str) != "BENIGN"]
            for fam in ["DDoS", "DoS", "PortScan", "BruteForce", "WebAttack", "Bot"]:
                subset = df[df["Label"].astype(str) == fam]
                if len(subset) >= 8:
                    self._pool[fam] = subset
            self._ready = True
        except Exception as exc:  # noqa: BLE001
            self._error = str(exc)
            self._ready = False

    def detect(self, attack_type: str, *, n_flows: int = 64, random_state: int = 42) -> DetectionResult:
        self.load()
        if not self._ready:
            fallback = detect_label_oracle(attack_type=attack_type)
            fallback.detail["fallback_reason"] = self._error or "detector_not_ready"
            return fallback
        t0 = time.perf_counter()
        pool = self._pool.get(attack_type)
        if pool is None or getattr(pool, "empty", True):
            pool = self._pool.get("_all_attack")
        if pool is None or getattr(pool, "empty", True):
            fallback = detect_label_oracle(attack_type=attack_type)
            fallback.detail["fallback_reason"] = "empty_attack_pool"
            return fallback
        sample = pool.sample(n=min(n_flows, len(pool)), random_state=random_state)
        X = self._bundle.transform(sample, task="binary")
        proba = self._binary.predict_proba(X)
        classes = list(getattr(self._binary, "classes_", [0, 1]))
        idx = classes.index(1) if 1 in classes else 1
        p_atk = proba[:, idx]
        detected = bool(
            float(np.mean(p_atk >= self.threshold)) >= 0.5 or float(np.max(p_atk)) >= self.threshold
        )
        conf = float(np.mean(p_atk))
        return DetectionResult(
            detected=detected,
            mode="frozen_ml",
            attack_type=attack_type,
            confidence=round(conf, 6),
            latency_s=time.perf_counter() - t0,
            n_flows_scored=int(len(sample)),
            detail={
                "threshold": self.threshold,
                "mean_proba": conf,
                "max_proba": float(np.max(p_atk)),
            },
        )


def detect_label_oracle(*, attack_type: str, confidence: float = 0.95) -> DetectionResult:
    """Deterministic detection for CI / offline hosts without scoring latency noise."""
    t0 = time.perf_counter()
    time.sleep(0.001)
    return DetectionResult(
        detected=True,
        mode="label_oracle",
        attack_type=attack_type,
        confidence=confidence,
        latency_s=time.perf_counter() - t0,
        n_flows_scored=0,
        detail={
            "note": "Oracle detection for harness CI; prefer frozen_ml when artifacts+data present"
        },
    )


def run_detection(
    *,
    attack_type: str,
    mode: DetectionMode = "frozen_ml",
    model_dir: Path | None = None,
    detector: FrozenDetector | None = None,
) -> DetectionResult:
    if mode == "label_oracle":
        return detect_label_oracle(attack_type=attack_type)
    if detector is not None:
        return detector.detect(attack_type)
    if model_dir is None:
        return detect_label_oracle(attack_type=attack_type)
    return FrozenDetector(model_dir=model_dir).detect(attack_type)
