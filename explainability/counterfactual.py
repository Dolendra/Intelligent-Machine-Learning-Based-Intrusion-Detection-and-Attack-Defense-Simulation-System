"""Simple what-if counterfactuals for IDS feature vectors (decision-support)."""
from __future__ import annotations

from typing import Any

import numpy as np

from ml.prediction.predictor import IDSPredictor


def suggest_counterfactuals(
    predictor: IDSPredictor,
    features: dict[str, float],
    *,
    top_features: list[dict[str, Any]] | None = None,
    background: np.ndarray | None = None,
    max_edits: int = 5,
    allow_missing: bool = False,
) -> dict[str, Any]:
    """Perturb top positive drivers toward background median and re-score.

    This is a controlled research aid — not an optimization attack or live defense.
    """
    base = predictor.predict_row(features, allow_missing=allow_missing)
    expected = list(predictor.bundle.feature_names)
    row = {k: float(features.get(k, 0.0)) for k in expected}

    # Background medians in raw feature space (approximate via zeros if unavailable)
    medians: dict[str, float] = {k: 0.0 for k in expected}
    if background is not None and background.ndim == 2 and background.shape[1] > 0:
        # background is usually already-selected/scaled; fall back to zero edits on raw
        pass

    drivers: list[str] = []
    if top_features:
        drivers = [
            str(t["feature"])
            for t in sorted(top_features, key=lambda x: float(x.get("contribution", 0)), reverse=True)
            if float(t.get("contribution", 0)) > 0
        ][:max_edits]
    if not drivers:
        # Use multiclass/binary importances as drivers
        model = predictor.multiclass_model if base.is_attack else predictor.binary_model
        names = predictor.bundle.selected_for("multiclass" if base.is_attack else "binary")
        if hasattr(model, "feature_importances_"):
            vals = np.asarray(model.feature_importances_, dtype=float)
            order = np.argsort(-vals)[:max_edits]
            drivers = [names[i] for i in order if i < len(names)]

    trials = []
    for feat in drivers:
        if feat not in row:
            continue
        edited = dict(row)
        original = edited[feat]
        # Pull toward a quieter value: 0 or half magnitude
        target = medians.get(feat, 0.0)
        edited[feat] = float(target)
        pred = predictor.predict_row(edited, allow_missing=True)
        trials.append(
            {
                "feature": feat,
                "original_value": original,
                "counterfactual_value": edited[feat],
                "new_attack_type": pred.attack_type,
                "new_is_attack": pred.is_attack,
                "new_binary_proba_attack": round(float(pred.binary_proba_attack), 4),
                "flipped_to_benign": bool(base.is_attack and not pred.is_attack),
                "family_changed": bool(pred.attack_type != base.attack_type),
            }
        )

    # Combined edit of all drivers
    combined = dict(row)
    for feat in drivers:
        if feat in combined:
            combined[feat] = float(medians.get(feat, 0.0))
    combined_pred = predictor.predict_row(combined, allow_missing=True) if drivers else base

    return {
        "method": "feature_median_perturbation",
        "advisory_only": True,
        "note": (
            "What-if edits set selected drivers toward a quiet baseline (0). "
            "Illustrative only — not a guaranteed minimal counterfactual."
        ),
        "baseline": {
            "attack_type": base.attack_type,
            "is_attack": base.is_attack,
            "binary_proba_attack": round(float(base.binary_proba_attack), 4),
        },
        "edits": trials,
        "combined": {
            "features_changed": drivers,
            "new_attack_type": combined_pred.attack_type,
            "new_is_attack": combined_pred.is_attack,
            "new_binary_proba_attack": round(float(combined_pred.binary_proba_attack), 4),
            "flipped_to_benign": bool(base.is_attack and not combined_pred.is_attack),
        },
    }
