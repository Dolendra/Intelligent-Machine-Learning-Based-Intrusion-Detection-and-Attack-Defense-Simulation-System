"""ml/evaluation/drift.py — simple feature / label distribution drift helpers."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def population_stability_index(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """PSI between two 1-D distributions (higher = more shift)."""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    expected = expected[np.isfinite(expected)]
    actual = actual[np.isfinite(actual)]
    if len(expected) < 20 or len(actual) < 20:
        return float("nan")
    qs = np.linspace(0, 100, bins + 1)
    cuts = np.unique(np.percentile(expected, qs))
    if len(cuts) < 3:
        return 0.0
    e_counts = np.histogram(expected, bins=cuts)[0].astype(float)
    a_counts = np.histogram(actual, bins=cuts)[0].astype(float)
    e_pct = (e_counts + 1e-6) / (e_counts.sum() + 1e-6 * len(e_counts))
    a_pct = (a_counts + 1e-6) / (a_counts.sum() + 1e-6 * len(a_counts))
    return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))


def mean_shift_z(expected: np.ndarray, actual: np.ndarray) -> float:
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    expected = expected[np.isfinite(expected)]
    actual = actual[np.isfinite(actual)]
    if len(expected) < 5 or len(actual) < 5:
        return float("nan")
    std = float(np.std(expected)) or 1.0
    return float((np.mean(actual) - np.mean(expected)) / std)


def feature_drift_report(
    ref_df: pd.DataFrame,
    cur_df: pd.DataFrame,
    feature_cols: list[str],
    *,
    top_k: int = 15,
) -> dict[str, Any]:
    rows = []
    for col in feature_cols:
        if col not in ref_df.columns or col not in cur_df.columns:
            continue
        psi = population_stability_index(ref_df[col].to_numpy(), cur_df[col].to_numpy())
        z = mean_shift_z(ref_df[col].to_numpy(), cur_df[col].to_numpy())
        rows.append({"feature": col, "psi": None if np.isnan(psi) else round(float(psi), 4), "mean_shift_z": None if np.isnan(z) else round(float(z), 4)})
    rows.sort(key=lambda r: abs(r["psi"] or 0), reverse=True)
    flagged = [r for r in rows if (r["psi"] or 0) >= 0.2]
    return {
        "n_ref": int(len(ref_df)),
        "n_cur": int(len(cur_df)),
        "features_compared": len(rows),
        "flagged_psi_ge_0.2": flagged[:top_k],
        "top_psi": rows[:top_k],
        "note": "PSI>=0.2 often treated as notable shift (heuristic, not a universal rule).",
    }


def label_drift_report(ref_labels: pd.Series, cur_labels: pd.Series) -> dict[str, Any]:
    ref_p = ref_labels.value_counts(normalize=True)
    cur_p = cur_labels.value_counts(normalize=True)
    keys = sorted(set(ref_p.index) | set(cur_p.index))
    deltas = []
    for k in keys:
        deltas.append(
            {
                "label": str(k),
                "ref_pct": round(float(ref_p.get(k, 0.0) * 100), 2),
                "cur_pct": round(float(cur_p.get(k, 0.0) * 100), 2),
                "delta_pp": round(float((cur_p.get(k, 0.0) - ref_p.get(k, 0.0)) * 100), 2),
            }
        )
    deltas.sort(key=lambda d: abs(d["delta_pp"]), reverse=True)
    return {"by_label": deltas}
