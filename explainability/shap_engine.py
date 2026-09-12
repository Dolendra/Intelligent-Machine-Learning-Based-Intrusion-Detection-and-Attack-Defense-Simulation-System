"""SHAP-based explainability for IDS predictions."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ml.features.pipeline import FeatureBundle
from ml.prediction.predictor import FeatureValidationError, IDSPredictor

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

    def explain(
        self,
        features: dict[str, float] | pd.DataFrame,
        top_k: int = 10,
        *,
        allow_missing: bool = False,
    ) -> dict[str, Any]:
        pred = self.predictor.predict_row(features, allow_missing=allow_missing)
        if isinstance(features, dict):
            df = pd.DataFrame([features])
        else:
            df = features.copy()

        expected = list(self.bundle.feature_names)
        missing = [c for c in expected if c not in df.columns]
        if missing and not allow_missing:
            raise FeatureValidationError(
                f"Invalid feature vector for explanation: missing {len(missing)} features."
            )
        for col in missing:
            df[col] = 0.0
        df = df[expected]
        X = self.bundle.transform(df)

        model = self.predictor.multiclass_model if pred.is_attack else self.predictor.binary_model
        class_index = self._predicted_class_index(model, pred)
        contributions, actual_method, fallback_used = self._explain_values(
            model, X, class_index=class_index
        )

        ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_k]
        positives = [(f, v) for f, v in ranked if v >= 0][:3]
        negatives = [(f, v) for f, v in ranked if v < 0][:2]
        narrative = self._narrative(pred.attack_type, positives, negatives, actual_method)

        return {
            "method": "shap" if not fallback_used else actual_method,
            "requested_method": "shap",
            "actual_method": actual_method,
            "fallback_used": fallback_used,
            "prediction": pred.attack_type,
            "is_attack": pred.is_attack,
            "predicted_class_index": class_index,
            "confidence": pred.binary_confidence if not pred.is_attack else pred.multiclass_confidence,
            "top_features": [{"feature": f, "contribution": float(v)} for f, v in ranked],
            "explanation": narrative,
        }

    def _predicted_class_index(self, model: Any, pred) -> int:
        classes = list(getattr(model, "classes_", []))
        if not classes:
            return 1 if pred.is_attack else 0
        # Binary attack index
        if not pred.is_attack:
            if 0 in classes:
                return classes.index(0)
            return 0
        # Multiclass: map attack_type label to encoded class
        try:
            encoded = int(self.bundle.label_encoder.transform([pred.attack_type])[0])
            if encoded in classes:
                return classes.index(encoded)
        except Exception:
            pass
        if 1 in classes and len(classes) == 2:
            return classes.index(1)
        return int(np.argmax(list(pred.class_probabilities.values())))

    def _explain_values(
        self, model: Any, X: np.ndarray, class_index: int
    ) -> tuple[dict[str, float], str, bool]:
        names = self.bundle.selected_features
        if HAS_SHAP:
            try:
                explainer = shap.TreeExplainer(model)
                sv = explainer.shap_values(X)
                values = self._select_class_shap(sv, class_index)
                return {n: float(v) for n, v in zip(names, values)}, "TreeExplainer", False
            except Exception:
                try:
                    bg = self.background if self.background is not None else X
                    bg = shap.sample(bg, min(50, len(bg)))
                    explainer = shap.KernelExplainer(model.predict_proba, bg)
                    sv = explainer.shap_values(X)
                    values = self._select_class_shap(sv, class_index)
                    return {n: float(v) for n, v in zip(names, values)}, "KernelExplainer", False
                except Exception:
                    pass

        if hasattr(model, "feature_importances_"):
            imp = model.feature_importances_
            return {n: float(v) for n, v in zip(names, imp)}, "feature_importance", True
        row = X[0]
        return {n: float(abs(v)) for n, v in zip(names, row)}, "abs_scaled_values", True

    @staticmethod
    def _select_class_shap(sv: Any, class_index: int) -> np.ndarray:
        if isinstance(sv, list):
            idx = min(max(class_index, 0), len(sv) - 1)
            return np.array(sv[idx])[0]
        arr = np.array(sv)
        if arr.ndim == 3:
            # (n_samples, n_features, n_classes) or (n_classes, n_samples, n_features)
            if arr.shape[0] < arr.shape[-1] and arr.shape[0] <= 20:
                idx = min(class_index, arr.shape[0] - 1)
                return arr[idx][0]
            idx = min(class_index, arr.shape[-1] - 1)
            return arr[0, :, idx]
        if arr.ndim == 2:
            return arr[0]
        return arr.reshape(-1)[: arr.size]

    @staticmethod
    def _narrative(
        attack_type: str,
        positives: list[tuple[str, float]],
        negatives: list[tuple[str, float]],
        actual_method: str,
    ) -> str:
        if not positives and not negatives:
            return f"The model classified this flow as {attack_type} ({actual_method})."
        parts = [f"Why was this classified as {attack_type}? ({actual_method})"]
        if positives:
            top = ", ".join(f"{f} ({v:+.3f})" for f, v in positives)
            parts.append(f"Strong positive contributors: {top}.")
        if negatives:
            top = ", ".join(f"{f} ({v:+.3f})" for f, v in negatives)
            parts.append(f"Counter-evidence: {top}.")
        parts.append("Positive values push toward the predicted class; negative values push against it.")
        return " ".join(parts)
