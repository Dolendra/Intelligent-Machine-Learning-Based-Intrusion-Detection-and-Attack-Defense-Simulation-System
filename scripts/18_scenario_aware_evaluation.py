"""Scenario-aware and regime-shift evaluation on the held-out test set.

Experiment 1 — IID: full test metrics (existing models)
Experiment 2 — Traffic-regime scenarios: intensity terciles
Experiment 3 — Attack-family leave-group scores (per Label)

Does not retrain; scores production joblibs under distribution slices.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path
from ml.evaluation.metrics import evaluate_binary, evaluate_multiclass
from ml.features.pipeline import FeatureBundle
from ml.models.factory import load_model
from ml.preprocessing.dataset import load_processed


def _proba_attack(model, X: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        p = model.predict_proba(X)
        if p.ndim == 2 and p.shape[1] >= 2:
            # Prefer positive/attack column via classes_
            if hasattr(model, "classes_"):
                classes = list(model.classes_)
                if 1 in classes:
                    return p[:, classes.index(1)]
                if "ATTACK" in [str(c) for c in classes]:
                    return p[:, [str(c) for c in classes].index("ATTACK")]
            return p[:, 1] if p.shape[1] == 2 else p.max(axis=1)
    return model.predict(X).astype(float)


def _score_slice(bundle, binary_model, multi_model, df: pd.DataFrame, threshold: float) -> dict:
    if len(df) < 20:
        return {"n": len(df), "skipped": True, "reason": "too_few_rows"}
    X_bin = bundle.transform(df, task="binary")
    y_bin = df["is_attack"].to_numpy()
    proba = _proba_attack(binary_model, X_bin)
    pred = (proba >= threshold).astype(int)
    binary = evaluate_binary(y_bin, pred, proba)

    attack_mask = y_bin == 1
    multi_metrics = None
    if attack_mask.sum() >= 10:
        X_m = bundle.transform(df.loc[attack_mask], task="multiclass")
        if X_m.shape[1] != getattr(multi_model, "n_features_in_", X_m.shape[1]):
            X_m = bundle.transform(df.loc[attack_mask], task="binary")
        y_true = bundle.encode_attack_labels(df.loc[attack_mask, "Label"])
        y_pred = multi_model.predict(X_m)
        labels = bundle.attack_class_names()
        multi_metrics = evaluate_multiclass(y_true, y_pred, labels=labels)
        # Keep compact per-class F1 from report if present
        if "report" in multi_metrics and isinstance(multi_metrics["report"], dict):
            multi_metrics = {
                k: multi_metrics[k]
                for k in ("accuracy", "f1_macro", "f1_weighted", "precision_macro", "recall_macro")
                if k in multi_metrics
            }

    return {
        "n": int(len(df)),
        "attack_rate": float(y_bin.mean()),
        "binary": {k: binary[k] for k in ("precision", "recall", "f1", "pr_auc", "fpr", "fnr", "mcc") if k in binary},
        "multiclass": multi_metrics,
    }


def _intensity_series(df: pd.DataFrame) -> pd.Series:
    cols = [c for c in ("Flow Packets/s", "Flow Bytes/s") if c in df.columns]
    if not cols:
        return pd.Series(np.zeros(len(df)), index=df.index)
    vals = df[cols].abs().max(axis=1)
    return vals


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    threshold = float(cfg.get("models", {}).get("binary_threshold", 0.5))

    required = [out_dir / "feature_bundle.joblib", out_dir / "binary_best.joblib", out_dir / "multiclass_best.joblib"]
    if not all(p.exists() for p in required):
        raise SystemExit("Trained models missing — run scripts/02_train_models.py first.")

    test = load_processed("test")
    bundle = FeatureBundle.load(out_dir / "feature_bundle.joblib")
    binary_model = load_model(out_dir / "binary_best.joblib")
    multi_model = load_model(out_dir / "multiclass_best.joblib")

    report: dict = {
        "experiment": "scenario_aware_evaluation",
        "threshold": threshold,
        "note": (
            "IID = random stratified test split. Traffic regimes = intensity terciles on the same test set "
            "(in-distribution scenario proxy). Attack-family slices measure rare-class stress."
        ),
        "experiments": {},
    }

    report["experiments"]["1_iid_test"] = _score_slice(bundle, binary_model, multi_model, test, threshold)

    intensity = _intensity_series(test)
    try:
        terciles = pd.qcut(intensity.rank(method="first"), 3, labels=["low", "mid", "high"])
    except ValueError:
        terciles = pd.Series(["all"] * len(test), index=test.index)

    regimes = {}
    for name in ("low", "mid", "high"):
        mask = terciles == name
        if mask.any():
            regimes[name] = _score_slice(bundle, binary_model, multi_model, test.loc[mask], threshold)
    report["experiments"]["2_traffic_regime_scenarios"] = regimes

    by_label = {}
    for label, group in test.groupby("Label"):
        by_label[str(label)] = _score_slice(bundle, binary_model, multi_model, group, threshold)
    report["experiments"]["3_attack_family_slices"] = by_label

    path = out_dir / "scenario_aware_evaluation.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    iid = report["experiments"]["1_iid_test"].get("binary", {})
    print(f"IID test F1={iid.get('f1')} recall={iid.get('recall')} PR-AUC={iid.get('pr_auc')}")
    for k, v in regimes.items():
        b = v.get("binary") or {}
        print(f"  regime {k}: n={v.get('n')} F1={b.get('f1')} FPR={b.get('fpr')}")


if __name__ == "__main__":
    main()
