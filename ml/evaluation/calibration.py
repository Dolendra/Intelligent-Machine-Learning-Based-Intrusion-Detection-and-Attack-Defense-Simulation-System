"""Probability calibration metrics for IDS binary detectors."""
from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss


def expected_calibration_error(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    n_bins: int = 10,
) -> float:
    """ECE over equal-width probability bins (attack class = 1)."""
    y_true = np.asarray(y_true).astype(int)
    y_proba = np.clip(np.asarray(y_proba, dtype=float), 0.0, 1.0)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    if n == 0:
        return 0.0
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_proba >= lo) & (y_proba < hi if i < n_bins - 1 else y_proba <= hi)
        if not np.any(mask):
            continue
        conf = float(y_proba[mask].mean())
        acc = float(y_true[mask].mean())
        ece += (mask.sum() / n) * abs(acc - conf)
    return float(ece)


def calibration_report(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    n_bins: int = 10,
) -> dict[str, Any]:
    """Brier score, ECE, and reliability curve points."""
    y_true = np.asarray(y_true).astype(int)
    y_proba = np.clip(np.asarray(y_proba, dtype=float), 0.0, 1.0)
    report: dict[str, Any] = {
        "brier_score": float(brier_score_loss(y_true, y_proba)),
        "ece": expected_calibration_error(y_true, y_proba, n_bins=n_bins),
        "n_bins": n_bins,
    }
    try:
        frac_pos, mean_pred = calibration_curve(y_true, y_proba, n_bins=n_bins, strategy="uniform")
        report["reliability_curve"] = {
            "fraction_of_positives": [float(x) for x in frac_pos],
            "mean_predicted_value": [float(x) for x in mean_pred],
        }
    except ValueError:
        report["reliability_curve"] = None
    return report
