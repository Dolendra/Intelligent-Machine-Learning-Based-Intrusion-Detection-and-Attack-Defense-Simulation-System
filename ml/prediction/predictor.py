"""Two-stage prediction: binary attack detection then attack-family classification."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from ids_config import load_config, resolve_path
from ml.features.pipeline import FeatureBundle
from ml.models.factory import load_model

Certainty = Literal["likely_benign", "uncertain", "likely_attack"]


class FeatureValidationError(ValueError):
    """Raised when the feature vector does not match the trained schema."""


@dataclass
class PredictionResult:
    is_attack: bool
    attack_type: str
    binary_confidence: float
    multiclass_confidence: float
    binary_proba_attack: float
    class_probabilities: dict[str, float]
    certainty: Certainty = "uncertain"
    threshold: float = 0.5
    uncertainty_lower: float = 0.30
    uncertainty_upper: float = 0.70
    missing_features: list[str] = field(default_factory=list)
    extra_features: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _load_operating_point() -> dict[str, float]:
    cfg = load_config()
    models = cfg.get("models", {})
    defaults = {
        "operating_threshold": float(models.get("binary_threshold", 0.5)),
        "uncertainty_lower": float(models.get("uncertainty_lower", 0.30)),
        "uncertainty_upper": float(models.get("uncertainty_upper", 0.70)),
    }
    path = resolve_path(models["output_dir"]) / "threshold_operating_point.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            defaults["operating_threshold"] = float(data.get("operating_threshold", defaults["operating_threshold"]))
            defaults["uncertainty_lower"] = float(data.get("uncertainty_lower", defaults["uncertainty_lower"]))
            defaults["uncertainty_upper"] = float(data.get("uncertainty_upper", defaults["uncertainty_upper"]))
        except Exception:
            pass
    lo, hi = defaults["uncertainty_lower"], defaults["uncertainty_upper"]
    if lo >= hi:
        defaults["uncertainty_lower"], defaults["uncertainty_upper"] = 0.30, 0.70
    return defaults


def clear_operating_point_cache() -> None:
    _load_operating_point.cache_clear()


class IDSPredictor:
    def __init__(
        self,
        feature_bundle: FeatureBundle,
        binary_model: Any,
        multiclass_model: Any,
        binary_threshold: float = 0.5,
        allow_missing_features: bool = False,
        uncertainty_lower: float = 0.30,
        uncertainty_upper: float = 0.70,
    ) -> None:
        self.bundle = feature_bundle
        self.binary_model = binary_model
        self.multiclass_model = multiclass_model
        self.binary_threshold = binary_threshold
        self.allow_missing_features = allow_missing_features
        self.uncertainty_lower = uncertainty_lower
        self.uncertainty_upper = uncertainty_upper
        self.calibrated_binary = False

    @classmethod
    def from_artifacts(cls, model_dir: Path | str | None = None) -> "IDSPredictor":
        cfg = load_config()
        directory = Path(model_dir) if model_dir else resolve_path(cfg["models"]["output_dir"])
        bundle = FeatureBundle.load(directory / "feature_bundle.joblib")
        use_cal = bool(cfg.get("models", {}).get("use_calibrated_binary", False))
        cal_path = directory / "binary_calibrated.joblib"
        if use_cal and cal_path.exists():
            binary = load_model(cal_path)
        else:
            binary = load_model(directory / "binary_best.joblib")
        multi = load_model(directory / "multiclass_best.joblib")
        op = _load_operating_point()
        pred = cls(
            bundle,
            binary,
            multi,
            binary_threshold=op["operating_threshold"],
            uncertainty_lower=op["uncertainty_lower"],
            uncertainty_upper=op["uncertainty_upper"],
        )
        pred.calibrated_binary = bool(use_cal and cal_path.exists())
        return pred

    def _attack_class_index(self, model: Any) -> int:
        classes = list(getattr(model, "classes_", [0, 1]))
        if 1 in classes:
            return classes.index(1)
        if "ATTACK" in classes:
            return classes.index("ATTACK")
        return 1 if len(classes) > 1 else 0

    def _proba_attack(self, model: Any, X: np.ndarray) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)
            idx = self._attack_class_index(model)
            return proba[:, idx]
        if hasattr(model, "decision_function"):
            scores = model.decision_function(X)
            return 1 / (1 + np.exp(-scores))
        return model.predict(X).astype(float)

    def _certainty(self, attack_proba: float) -> Certainty:
        if attack_proba < self.uncertainty_lower:
            return "likely_benign"
        if attack_proba > self.uncertainty_upper:
            return "likely_attack"
        return "uncertain"

    def _decode_family_classes(self, raw_classes: list[Any]) -> list[str]:
        if raw_classes and isinstance(raw_classes[0], (int, np.integer)):
            try:
                return [str(c) for c in self.bundle.decode_attack_labels(np.asarray(raw_classes))]
            except Exception:
                try:
                    return [str(c) for c in self.bundle.label_encoder.inverse_transform(raw_classes)]
                except Exception:
                    return [str(c) for c in raw_classes]
        return [str(c) for c in raw_classes]

    def _family_probabilities(self, multi_proba: np.ndarray) -> tuple[str, float, dict[str, float]]:
        """Map multiclass proba to attack-family distribution (exclude BENIGN if present)."""
        if hasattr(self.multiclass_model, "classes_"):
            classes = self._decode_family_classes(list(self.multiclass_model.classes_))
        else:
            classes = self.bundle.attack_class_names()
        class_probs = {cls: float(p) for cls, p in zip(classes, multi_proba)}
        # Drop BENIGN if an older model still emits it after Stage-1 attack
        attack_probs = {k: v for k, v in class_probs.items() if k != "BENIGN"}
        if not attack_probs:
            attack_probs = class_probs
        total = sum(attack_probs.values()) or 1.0
        attack_probs = {k: v / total for k, v in attack_probs.items()}
        ranked = sorted(attack_probs.items(), key=lambda kv: kv[1], reverse=True)
        attack_type = ranked[0][0]
        return attack_type, float(ranked[0][1]), attack_probs

    def _prepare_frame(
        self,
        features: dict[str, float] | pd.Series | pd.DataFrame,
        *,
        allow_missing: bool | None = None,
    ) -> tuple[pd.DataFrame, list[str], list[str]]:
        allow_missing = self.allow_missing_features if allow_missing is None else allow_missing
        if isinstance(features, dict):
            df = pd.DataFrame([features])
        elif isinstance(features, pd.Series):
            df = features.to_frame().T
        else:
            df = features.copy()

        expected = list(self.bundle.feature_names)
        missing = [c for c in expected if c not in df.columns]
        extra = [c for c in df.columns if c not in expected and c not in ("Label", "is_attack")]

        if missing and not allow_missing:
            raise FeatureValidationError(
                f"Invalid feature vector: expected {len(expected)} features, "
                f"missing {len(missing)} ({', '.join(missing[:8])}{'...' if len(missing) > 8 else ''})."
            )
        for col in missing:
            df[col] = 0.0
        df = df[expected]
        return df, missing, extra

    def predict_row(
        self,
        features: dict[str, float] | pd.Series | pd.DataFrame,
        *,
        allow_missing: bool | None = None,
    ) -> PredictionResult:
        df, missing, extra = self._prepare_frame(features, allow_missing=allow_missing)
        X_bin = self.bundle.transform(df, task="binary")
        attack_proba = float(self._proba_attack(self.binary_model, X_bin)[0])
        is_attack = attack_proba >= self.binary_threshold
        certainty = self._certainty(attack_proba)

        if not is_attack:
            return PredictionResult(
                is_attack=False,
                attack_type="BENIGN",
                binary_confidence=float(1.0 - attack_proba),
                multiclass_confidence=float(1.0 - attack_proba),
                binary_proba_attack=attack_proba,
                class_probabilities={"BENIGN": float(1.0 - attack_proba), "ATTACK": attack_proba},
                certainty=certainty,
                threshold=self.binary_threshold,
                uncertainty_lower=self.uncertainty_lower,
                uncertainty_upper=self.uncertainty_upper,
                missing_features=missing,
                extra_features=extra,
            )

        X_multi = self.bundle.transform(df, task="multiclass")
        if X_multi.shape[1] != getattr(self.multiclass_model, "n_features_in_", X_multi.shape[1]):
            X_multi = X_bin
        multi_proba = self.multiclass_model.predict_proba(X_multi)[0]
        attack_type, multi_conf, class_probs = self._family_probabilities(multi_proba)

        return PredictionResult(
            is_attack=True,
            attack_type=attack_type,
            binary_confidence=attack_proba,
            multiclass_confidence=multi_conf,
            binary_proba_attack=attack_proba,
            class_probabilities=class_probs,
            certainty=certainty,
            threshold=self.binary_threshold,
            uncertainty_lower=self.uncertainty_lower,
            uncertainty_upper=self.uncertainty_upper,
            missing_features=missing,
            extra_features=extra,
        )

    def predict_many(self, df: pd.DataFrame) -> list[PredictionResult]:
        return self.predict_many_vectorized(df, allow_missing=True)

    def predict_many_vectorized(
        self,
        df: pd.DataFrame,
        *,
        allow_missing: bool | None = None,
    ) -> list[PredictionResult]:
        allow_missing = self.allow_missing_features if allow_missing is None else allow_missing
        work = df.copy()
        expected = list(self.bundle.feature_names)
        missing = [c for c in expected if c not in work.columns]
        if missing and not allow_missing:
            raise FeatureValidationError(
                f"Invalid batch feature matrix: missing {len(missing)} columns "
                f"({', '.join(missing[:8])}{'...' if len(missing) > 8 else ''})."
            )
        for col in missing:
            work[col] = 0.0
        work = work[expected]
        X_bin = self.bundle.transform(work, task="binary")
        attack_proba = self._proba_attack(self.binary_model, X_bin)
        is_attack = attack_proba >= self.binary_threshold

        multi_proba = None
        if np.any(is_attack):
            X_multi = self.bundle.transform(work, task="multiclass")
            if X_multi.shape[1] != getattr(self.multiclass_model, "n_features_in_", X_multi.shape[1]):
                X_multi = X_bin
            multi_proba = self.multiclass_model.predict_proba(X_multi)

        results: list[PredictionResult] = []
        for i in range(len(work)):
            p_atk = float(attack_proba[i])
            certainty = self._certainty(p_atk)
            if not bool(is_attack[i]):
                results.append(
                    PredictionResult(
                        is_attack=False,
                        attack_type="BENIGN",
                        binary_confidence=float(1.0 - p_atk),
                        multiclass_confidence=float(1.0 - p_atk),
                        binary_proba_attack=p_atk,
                        class_probabilities={"BENIGN": float(1.0 - p_atk), "ATTACK": p_atk},
                        certainty=certainty,
                        threshold=self.binary_threshold,
                        uncertainty_lower=self.uncertainty_lower,
                        uncertainty_upper=self.uncertainty_upper,
                        missing_features=missing,
                    )
                )
                continue
            attack_type, multi_conf, class_probs = self._family_probabilities(multi_proba[i])
            results.append(
                PredictionResult(
                    is_attack=True,
                    attack_type=attack_type,
                    binary_confidence=p_atk,
                    multiclass_confidence=multi_conf,
                    binary_proba_attack=p_atk,
                    class_probabilities=class_probs,
                    certainty=certainty,
                    threshold=self.binary_threshold,
                    uncertainty_lower=self.uncertainty_lower,
                    uncertainty_upper=self.uncertainty_upper,
                    missing_features=missing,
                )
            )
        return results
