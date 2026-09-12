"""Evaluation metrics for IDS models (precision/recall prioritized)."""
from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_binary(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray | None = None) -> dict[str, Any]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (cm.ravel().tolist() + [0, 0, 0, 0])[:4]
    # Guard when a class is missing in a tiny sample
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    else:
        tn = fp = fn = tp = 0
        for yt, yp in zip(y_true, y_pred):
            if yt == 0 and yp == 0:
                tn += 1
            elif yt == 0 and yp == 1:
                fp += 1
            elif yt == 1 and yp == 0:
                fn += 1
            elif yt == 1 and yp == 1:
                tp += 1

    fpr = float(fp / (fp + tn)) if (fp + tn) else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) else 0.0
    specificity = float(tn / (tn + fp)) if (tn + fp) else 0.0

    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "specificity": specificity,
        "fpr": fpr,
        "fnr": fnr,
        "mcc": float(matthews_corrcoef(y_true, y_pred)) if len(np.unique(y_true)) > 1 else 0.0,
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }
    if y_proba is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
        except ValueError:
            metrics["roc_auc"] = None
        try:
            metrics["pr_auc"] = float(average_precision_score(y_true, y_proba))
        except ValueError:
            metrics["pr_auc"] = None
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
