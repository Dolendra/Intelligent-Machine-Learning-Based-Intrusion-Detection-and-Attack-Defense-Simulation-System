"""Global and attack-family feature importance summaries (research XAI)."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from ml.prediction.predictor import IDSPredictor


def _importance_vector(model: Any, names: list[str]) -> list[dict[str, float | str]]:
    if hasattr(model, "feature_importances_"):
        vals = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_, dtype=float)
        vals = np.abs(coef).mean(axis=0) if coef.ndim > 1 else np.abs(coef)
    else:
        return []
    n = min(len(names), len(vals))
    pairs = sorted(
        ((names[i], float(vals[i])) for i in range(n)),
        key=lambda kv: abs(kv[1]),
        reverse=True,
    )
    return [{"feature": f, "importance": v} for f, v in pairs]


def global_model_importance(predictor: IDSPredictor, top_k: int = 15) -> dict[str, Any]:
    """Fast global ranking from model coefficients / importances (not sample SHAP)."""
    bin_names = predictor.bundle.selected_for("binary")
    multi_names = predictor.bundle.selected_for("multiclass")
    binary = _importance_vector(predictor.binary_model, bin_names)[:top_k]
    multiclass = _importance_vector(predictor.multiclass_model, multi_names)[:top_k]
    return {
        "method": "model_feature_importance",
        "note": (
            "Global ranking from the fitted model (feature_importances_ / |coef_|). "
            "Complement local SHAP/LIME; not a substitute for per-flow explanations."
        ),
        "binary_top": binary,
        "multiclass_top": multiclass,
    }


def attack_specific_from_explanations(
    rows: list[dict[str, Any]],
    top_k: int = 10,
) -> dict[str, Any]:
    """Aggregate |contribution| by predicted attack family from local explanations."""
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        attack = str(row.get("prediction") or row.get("attack_type") or "UNKNOWN")
        counts[attack] += 1
        for item in row.get("top_features") or []:
            feat = str(item.get("feature"))
            val = abs(float(item.get("contribution", 0.0)))
            buckets[attack][feat].append(val)

    by_attack: dict[str, Any] = {}
    for attack, feats in buckets.items():
        ranked = sorted(
            (
                {"feature": f, "mean_abs_contribution": float(np.mean(vs)), "n": len(vs)}
                for f, vs in feats.items()
            ),
            key=lambda x: x["mean_abs_contribution"],
            reverse=True,
        )[:top_k]
        by_attack[attack] = {"samples": counts[attack], "top_features": ranked}

    return {
        "method": "mean_abs_local_explanation",
        "note": "Attack-specific rankings averaged from local explanations on sampled flows.",
        "by_attack": by_attack,
        "attacks": sorted(by_attack.keys()),
    }
