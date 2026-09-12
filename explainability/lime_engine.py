"""LIME-based secondary explainability for IDS predictions."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ml.features.pipeline import FeatureBundle
from ml.prediction.predictor import IDSPredictor

try:
    from lime.lime_tabular import LimeTabularExplainer

    HAS_LIME = True
except ImportError:  # pragma: no cover
    HAS_LIME = False


class LimeExplanationEngine:
    """Local surrogate explanations (complementary to SHAP)."""

    def __init__(self, predictor: IDSPredictor, background: np.ndarray | None = None) -> None:
        self.predictor = predictor
        self.bundle: FeatureBundle = predictor.bundle
        self.background = background

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
        task = "multiclass" if pred.is_attack else "binary"
        X = self.bundle.transform(df, task=task)
        model = self.predictor.multiclass_model if pred.is_attack else self.predictor.binary_model
        expected_n = getattr(model, "n_features_in_", None)
        if expected_n is not None and X.shape[1] != expected_n:
            X = self.bundle.transform(df, task="binary")
            task = "binary"
        names = self.bundle.selected_for(task)

        contributions = self._lime_or_fallback(model, X, names, pred.is_attack, top_k)
        ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_k]
        top = ", ".join(f"{f} ({v:+.3f})" for f, v in ranked[:3]) if ranked else "n/a"
        narrative = (
            f"LIME local explanation for {pred.attack_type}: strongest local drivers are {top}. "
            "LIME fits a sparse linear surrogate around this instance."
        )
        return {
            "method": "lime",
            "prediction": pred.attack_type,
            "is_attack": pred.is_attack,
            "confidence": pred.binary_confidence if not pred.is_attack else pred.multiclass_confidence,
            "top_features": [{"feature": f, "contribution": float(v)} for f, v in ranked],
            "explanation": narrative,
            "available": HAS_LIME,
        }

    def _lime_or_fallback(
        self,
        model: Any,
        X: np.ndarray,
        names: list[str],
        is_attack: bool,
        top_k: int,
    ) -> dict[str, float]:
        if HAS_LIME and self.background is not None and len(self.background) >= 10:
            try:
                class_names = (
                    list(self.bundle.label_encoder.classes_)
                    if is_attack
                    else ["BENIGN", "ATTACK"]
                )
                explainer = LimeTabularExplainer(
                    self.background,
                    feature_names=names,
                    class_names=class_names,
                    discretize_continuous=True,
                    mode="classification",
                )

                def predict_fn(data: np.ndarray) -> np.ndarray:
                    return model.predict_proba(data)

                proba = model.predict_proba(X)[0]
                label_idx = int(np.argmax(proba))
                exp = explainer.explain_instance(
                    X[0],
                    predict_fn,
                    num_features=min(top_k, len(names)),
                    labels=(label_idx,),
                )
                pairs = exp.as_list(label=label_idx)
                out: dict[str, float] = {}
                for feat_desc, weight in pairs:
                    matched = next((n for n in names if n in str(feat_desc)), str(feat_desc))
                    out[matched] = float(weight)
                return out
            except Exception:
                pass

        if hasattr(model, "feature_importances_"):
            return {n: float(v) for n, v in zip(names, model.feature_importances_)}
        return {n: float(abs(v)) for n, v in zip(names, X[0])}
