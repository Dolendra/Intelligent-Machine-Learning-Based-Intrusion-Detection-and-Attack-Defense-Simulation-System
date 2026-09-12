"""Multi-objective model selection for IDS (project-justified weights)."""
from __future__ import annotations

from typing import Any


def binary_selection_score(metrics: dict[str, Any], weights: dict[str, float] | None = None) -> float:
    """
    Higher is better. Default weights emphasize recall for IDS, then F1/PR-AUC,
    penalize FPR, and lightly reward faster inference.
    """
    w = {
        "recall": 0.30,
        "f1": 0.25,
        "pr_auc": 0.20,
        "fpr": 0.15,  # lower better — inverted below
        "latency": 0.10,  # lower better — inverted below
    }
    if weights:
        w.update({k: float(v) for k, v in weights.items()})

    recall = float(metrics.get("recall") or 0.0)
    f1 = float(metrics.get("f1") or 0.0)
    pr = metrics.get("pr_auc")
    pr_auc = float(pr) if pr is not None else f1
    fpr = float(metrics.get("fpr") or 0.0)
    infer = float(metrics.get("infer_seconds_val") or 0.0)
    # Map latency to [0,1] score: ~0s → 1.0, >=2s → 0.0
    latency_score = max(0.0, 1.0 - min(1.0, infer / 2.0))
    fpr_score = max(0.0, 1.0 - fpr)

    total_w = sum(w.values()) or 1.0
    score = (
        w["recall"] * recall
        + w["f1"] * f1
        + w["pr_auc"] * pr_auc
        + w["fpr"] * fpr_score
        + w["latency"] * latency_score
    ) / total_w
    return float(score)


def multiclass_selection_score(metrics: dict[str, Any]) -> float:
    """Prefer macro-F1 with a secondary nudge from weighted-F1."""
    macro = float(metrics.get("f1_macro") or 0.0)
    weighted = float(metrics.get("f1_weighted") or 0.0)
    return 0.7 * macro + 0.3 * weighted
