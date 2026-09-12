"""Two-stage prediction: binary attack detection then attack-family classification."""
from __future__ import annotations

from dataclasses import dataclass, field
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
    missing_features: list[str] = field(default_factory=list)
    extra_features: list[str] = field(default_factory=list)


class IDSPredictor:
    def __init__(
        self,
        feature_bundle: FeatureBundle,
        binary_model: Any,
        multiclass_model: Any,
        binary_threshold: float = 0.5,
        allow_missing_features: bool = False,
    ) -> None:
        self.bundle = feature_bundle
        self.binary_model = binary_model
        self.multiclass_model = multiclass_model
        self.binary_threshold = binary_threshold
        self.allow_missing_features = allow_missing_features

    @classmethod
    def from_artifacts(cls, model_dir: Path | str | None = None) -> "IDSPredictor":
        cfg = load_config()
        directory = Path(model_dir) if model_dir else resolve_path(cfg["models"]["output_dir"])
        bundle = FeatureBundle.load(directory / "feature_bundle.joblib")
        binary = load_model(directory / "binary_best.joblib")
        multi = load_model(directory / "multiclass_best.joblib")
        threshold = float(cfg.get("models", {}).get("binary_threshold", 0.5))
        return cls(bundle, binary, multi, binary_threshold=threshold)

    def _attack_class_index(self, model: Any) -> int:
        classes = list(getattr(model, "classes_", [0, 1]))
        if 1 in classes:
            return classes.index(1)
        if "ATTACK" in classes:
            return classes.index("ATTACK")
        # Fallback: highest label index for binary
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
        if attack_proba < 0.30:
            return "likely_benign"
        if attack_proba > 0.70:
            return "likely_attack"
        return "uncertain"

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
        X = self.bundle.transform(df)
        attack_proba = float(self._proba_attack(self.binary_model, X)[0])
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
                missing_features=missing,
                extra_features=extra,
            )

        multi_proba = self.multiclass_model.predict_proba(X)[0]
        # Prefer model.classes_ when available; fall back to label encoder
        if hasattr(self.multiclass_model, "classes_"):
            raw_classes = list(self.multiclass_model.classes_)
            # classes_ may be encoded ints
            if raw_classes and isinstance(raw_classes[0], (int, np.integer)):
                classes = list(self.bundle.label_encoder.inverse_transform(raw_classes))
            else:
                classes = [str(c) for c in raw_classes]
        else:
            classes = list(self.bundle.label_encoder.classes_)

        class_probs = {cls: float(p) for cls, p in zip(classes, multi_proba)}
        ranked = sorted(class_probs.items(), key=lambda kv: kv[1], reverse=True)
        attack_type = ranked[0][0]
        if attack_type == "BENIGN" and len(ranked) > 1:
            attack_type = ranked[1][0]
        multi_conf = float(class_probs.get(attack_type, 0.0))

        return PredictionResult(
            is_attack=True,
            attack_type=attack_type,
            binary_confidence=attack_proba,
            multiclass_confidence=multi_conf,
            binary_proba_attack=attack_proba,
            class_probabilities=class_probs,
            certainty=certainty,
            threshold=self.binary_threshold,
            missing_features=missing,
            extra_features=extra,
        )

    def predict_many(self, df: pd.DataFrame) -> list[PredictionResult]:
        return [self.predict_row(df.iloc[[i]]) for i in range(len(df))]
