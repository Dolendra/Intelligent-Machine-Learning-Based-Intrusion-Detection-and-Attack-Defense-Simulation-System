"""Two-stage prediction: binary attack detection then attack-family classification."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ids_config import load_config, resolve_path
from ml.features.pipeline import FeatureBundle
from ml.models.factory import load_model


@dataclass
class PredictionResult:
    is_attack: bool
    attack_type: str
    binary_confidence: float
    multiclass_confidence: float
    binary_proba_attack: float
    class_probabilities: dict[str, float]


class IDSPredictor:
    def __init__(
        self,
        feature_bundle: FeatureBundle,
        binary_model: Any,
        multiclass_model: Any,
    ) -> None:
        self.bundle = feature_bundle
        self.binary_model = binary_model
        self.multiclass_model = multiclass_model

    @classmethod
    def from_artifacts(cls, model_dir: Path | str | None = None) -> "IDSPredictor":
        cfg = load_config()
        directory = Path(model_dir) if model_dir else resolve_path(cfg["models"]["output_dir"])
        bundle = FeatureBundle.load(directory / "feature_bundle.joblib")
        binary = load_model(directory / "binary_best.joblib")
        multi = load_model(directory / "multiclass_best.joblib")
        return cls(bundle, binary, multi)

    def _proba_positive(self, model: Any, X: np.ndarray) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)
            # Assume class 1 is attack for binary
            if proba.shape[1] == 2:
                return proba[:, 1]
            return proba.max(axis=1)
        # Decision function fallback
        if hasattr(model, "decision_function"):
            scores = model.decision_function(X)
            return 1 / (1 + np.exp(-scores))
        return model.predict(X).astype(float)

    def predict_row(self, features: dict[str, float] | pd.Series | pd.DataFrame) -> PredictionResult:
        if isinstance(features, dict):
            df = pd.DataFrame([features])
        elif isinstance(features, pd.Series):
            df = features.to_frame().T
        else:
            df = features

        # Ensure all expected columns exist
        for col in self.bundle.feature_names:
            if col not in df.columns:
                df[col] = 0.0
        df = df[self.bundle.feature_names]

        X = self.bundle.transform(df)
        attack_proba = float(self._proba_positive(self.binary_model, X)[0])
        is_attack = attack_proba >= 0.5
        binary_pred = int(is_attack)

        if not is_attack:
            return PredictionResult(
                is_attack=False,
                attack_type="BENIGN",
                binary_confidence=float(1.0 - attack_proba),
                multiclass_confidence=float(1.0 - attack_proba),
                binary_proba_attack=attack_proba,
                class_probabilities={"BENIGN": float(1.0 - attack_proba), "ATTACK": attack_proba},
            )

        multi_proba = self.multiclass_model.predict_proba(X)[0]
        classes = list(self.bundle.label_encoder.classes_)
        # Prefer non-benign class among multiclass outputs when binary says attack
        class_probs = {cls: float(p) for cls, p in zip(classes, multi_proba)}
        # Zero-out BENIGN for attack branch presentation if present
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
        )

    def predict_many(self, df: pd.DataFrame) -> list[PredictionResult]:
        return [self.predict_row(df.iloc[[i]]) for i in range(len(df))]
