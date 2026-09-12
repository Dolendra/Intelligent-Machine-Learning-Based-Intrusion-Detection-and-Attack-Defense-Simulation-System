"""XAI agreement / stability helpers (research evaluation)."""
from __future__ import annotations

from typing import Any

import numpy as np


def feature_ranks(top_features: list[dict[str, Any]], top_k: int = 10) -> dict[str, int]:
    """Map feature name → rank (1 = strongest |contribution|)."""
    ranked = sorted(top_features, key=lambda x: abs(float(x.get("contribution", 0))), reverse=True)[:top_k]
    return {str(item["feature"]): i + 1 for i, item in enumerate(ranked)}


def spearman_rank_correlation(ranks_a: dict[str, int], ranks_b: dict[str, int]) -> float | None:
    """Spearman ρ on shared features; None if fewer than 2 overlaps."""
    shared = sorted(set(ranks_a) & set(ranks_b))
    if len(shared) < 2:
        return None
    a = np.array([ranks_a[f] for f in shared], dtype=float)
    b = np.array([ranks_b[f] for f in shared], dtype=float)
    a_mean, b_mean = a.mean(), b.mean()
    num = ((a - a_mean) * (b - b_mean)).sum()
    den = np.sqrt(((a - a_mean) ** 2).sum() * ((b - b_mean) ** 2).sum())
    if den == 0:
        return 1.0 if np.allclose(a, b) else 0.0
    return float(num / den)


def top_k_overlap(ranks_a: dict[str, int], ranks_b: dict[str, int], k: int = 5) -> float:
    set_a = {f for f, r in ranks_a.items() if r <= k}
    set_b = {f for f, r in ranks_b.items() if r <= k}
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / max(1, len(set_a | set_b))


def compare_explanations(
    shap_top: list[dict[str, Any]],
    lime_top: list[dict[str, Any]],
    importance_top: list[dict[str, Any]] | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    shap_r = feature_ranks(shap_top, top_k)
    lime_r = feature_ranks(lime_top, top_k)
    out: dict[str, Any] = {
        "shap_vs_lime": {
            "spearman": spearman_rank_correlation(shap_r, lime_r),
            "top5_jaccard": top_k_overlap(shap_r, lime_r, 5),
        }
    }
    if importance_top:
        imp_r = feature_ranks(importance_top, top_k)
        out["shap_vs_importance"] = {
            "spearman": spearman_rank_correlation(shap_r, imp_r),
            "top5_jaccard": top_k_overlap(shap_r, imp_r, 5),
        }
        out["lime_vs_importance"] = {
            "spearman": spearman_rank_correlation(lime_r, imp_r),
            "top5_jaccard": top_k_overlap(lime_r, imp_r, 5),
        }
    return out
