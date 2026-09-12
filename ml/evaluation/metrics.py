"""Evaluation metrics for IDS models (precision/recall prioritized)."""
from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_binary(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray | None = None) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }
    if y_proba is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
        except ValueError:
            metrics["roc_auc"] = None
    return metrics


def evaluate_multiclass(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    label_ids = list(range(len(labels))) if labels is not None else None
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0, labels=label_ids)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0, labels=label_ids)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0, labels=label_ids)),
        "precision_weighted": float(
            precision_score(y_true, y_pred, average="weighted", zero_division=0, labels=label_ids)
        ),
        "recall_weighted": float(recall_score(y_true, y_pred, average="weighted", zero_division=0, labels=label_ids)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0, labels=label_ids)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=label_ids).tolist(),
        "report": classification_report(
            y_true,
            y_pred,
            labels=label_ids,
            target_names=labels,
            zero_division=0,
            output_dict=True,
        ),
    }
