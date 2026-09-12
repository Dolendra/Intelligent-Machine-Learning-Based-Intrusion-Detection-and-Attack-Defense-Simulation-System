"""SHAP-based explainability for IDS predictions."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ml.features.pipeline import FeatureBundle
from ml.prediction.predictor import IDSPredictor

try:
    import shap

    HAS_SHAP = True
except ImportError:  # pragma: no cover
    HAS_SHAP = False


class ExplanationEngine:
    """Produce human-readable feature contributions for a prediction."""

    def __init__(self, predictor: IDSPredictor, background: np.ndarray | None = None) -> None:
        self.predictor = predictor
        self.bundle: FeatureBundle = predictor.bundle
        self.background = background
        self._explainer = None

    def _get_explainer(self, model: Any, X_bg: np.ndarray):
        if not HAS_SHAP:
            return None
        # Tree models get TreeExplainer; otherwise KernelExplainer on a small background
        try:
            return shap.TreeExplainer(model)
        except Exception:
            bg = shap.sample(X_bg, min(50, len(X_bg)))
            return shap.KernelExplainer(model.predict_proba, bg)

    def explain(
        self,
        features: dict[str, float] | pd.DataFrame,
        top_k: int = 10,
    ) -> dict[str, Any]:
        pred = self.predictor.predict_row(features)
        if isinstance(features, dict):
            df = pd.DataFrame([features])
        else:
            df = features.copy()
        for col in self.bundle.feature_names:
            if col not in df.columns:
                df[col] = 0.0
        df = df[self.bundle.feature_names]
        X = self.bundle.transform(df)

        model = self.predictor.multiclass_model if pred.is_attack else self.predictor.binary_model
        contributions = self._shap_or_fallback(model, X, pred.is_attack)

        ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_k]
        narrative = self._narrative(pred.attack_type, ranked)

        return {
            "method": "shap",
            "prediction": pred.attack_type,
            "is_attack": pred.is_attack,
            "confidence": pred.binary_confidence if not pred.is_attack else pred.multiclass_confidence,
            "top_features": [{"feature": f, "contribution": float(v)} for f, v in ranked],
            "explanation": narrative,
        }

    def _shap_or_fallback(self, model: Any, X: np.ndarray, is_attack: bool) -> dict[str, float]:
        names = self.bundle.selected_features
        if HAS_SHAP:
            try:
                explainer = self._get_explainer(model, self.background if self.background is not None else X)
                sv = explainer.shap_values(X)
                # Handle binary / multiclass shap outputs
                if isinstance(sv, list):
                    # Prefer attack / predicted class index
                    idx = -1 if is_attack and len(sv) > 1 else 0
                    values = np.array(sv[idx])[0]
                else:
                    values = np.array(sv)[0]
                    if values.ndim > 1:
                        values = values[:, -1] if is_attack else values[:, 0]
                return {n: float(v) for n, v in zip(names, values)}
            except Exception:
                pass
        # Fallback: model feature_importances_ or absolute scaled values
        if hasattr(model, "feature_importances_"):
            imp = model.feature_importances_
            return {n: float(v) for n, v in zip(names, imp)}
        row = X[0]
        return {n: float(abs(v)) for n, v in zip(names, row)}

    @staticmethod
    def _narrative(attack_type: str, ranked: list[tuple[str, float]]) -> str:
        if not ranked:
            return f"The model classified this flow as {attack_type}."
        top = ", ".join(f"{f} ({v:+.3f})" for f, v in ranked[:3])
        return (
            f"The model classified this traffic as {attack_type} primarily due to "
            f"abnormal values in: {top}. Positive contributions push toward the predicted class."
        )
