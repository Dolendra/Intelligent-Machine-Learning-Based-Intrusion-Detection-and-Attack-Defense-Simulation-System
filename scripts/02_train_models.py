"""Train binary + multiclass IDS models and persist the best artifacts."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path
from ml.evaluation.metrics import evaluate_binary, evaluate_multiclass
from ml.features.pipeline import fit_feature_pipeline, transform_split
from ml.models.factory import build_model, save_model
from ml.preprocessing.dataset import load_processed


def _predict_proba_pos(model, X):
    if hasattr(model, "predict_proba"):
        p = model.predict_proba(X)
        return p[:, 1] if p.shape[1] == 2 else p.max(axis=1)
    return None


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading processed splits...")
    train = load_processed("train")
    val = load_processed("val")
    test = load_processed("test")

    print("Fitting feature pipeline on train only...")
    bundle, X_train, y_bin_train, y_multi_train = fit_feature_pipeline(train)
    X_val, y_bin_val, y_multi_val = transform_split(bundle, val)
    X_test, y_bin_test, y_multi_test = transform_split(bundle, test)
    bundle.save(out_dir / "feature_bundle.joblib")
    print(f"Selected {len(bundle.selected_features)} features")

    binary_results = {}
    best_binary_name = None
    best_binary_f1 = -1.0
    best_binary_model = None

    print("\n=== Stage 1: Binary classification (BENIGN vs ATTACK) ===")
    for name in cfg["models"]["binary"]["algorithms"]:
        model = build_model(name, cfg["data"]["random_state"])
        t0 = time.perf_counter()
        model.fit(X_train, y_bin_train)
        train_time = time.perf_counter() - t0
        t1 = time.perf_counter()
        pred = model.predict(X_val)
        infer = time.perf_counter() - t1
        proba = _predict_proba_pos(model, X_val)
        metrics = evaluate_binary(y_bin_val, pred, proba)
        metrics["train_seconds"] = round(train_time, 3)
        metrics["infer_seconds_val"] = round(infer, 4)
        binary_results[name] = metrics
        pr = metrics.get("pr_auc")
        pr_s = f"{pr:.4f}" if pr is not None else "n/a"
        print(
            f"  {name}: F1={metrics['f1']:.4f} Recall={metrics['recall']:.4f} "
            f"Prec={metrics['precision']:.4f} PR-AUC={pr_s} "
            f"FPR={metrics.get('fpr', float('nan')):.4f} FNR={metrics.get('fnr', float('nan')):.4f}"
        )
        # Primary selection: F1; PR-AUC logged for imbalance-aware reporting
        if metrics["f1"] > best_binary_f1:
            best_binary_f1 = metrics["f1"]
            best_binary_name = name
            best_binary_model = model

    save_model(best_binary_model, out_dir / "binary_best.joblib")
    print(f"Best binary model: {best_binary_name} (selected by validation F1; see PR-AUC/FPR/FNR in report)")

    # Multiclass: train on all rows (including benign) so labels stay consistent
    multi_results = {}
    best_multi_name = None
    best_multi_f1 = -1.0
    best_multi_model = None
    class_names = list(bundle.label_encoder.classes_)

    print("\n=== Stage 2: Attack-family classification ===")
    for name in cfg["models"]["multiclass"]["algorithms"]:
        model = build_model(name, cfg["data"]["random_state"])
        t0 = time.perf_counter()
        model.fit(X_train, y_multi_train)
        train_time = time.perf_counter() - t0
        pred = model.predict(X_val)
        metrics = evaluate_multiclass(y_multi_val, pred, labels=class_names)
        metrics["train_seconds"] = round(train_time, 3)
        multi_results[name] = {k: v for k, v in metrics.items() if k != "report"}
        multi_results[name]["report"] = metrics["report"]
        print(f"  {name}: macro-F1={metrics['f1_macro']:.4f} weighted-F1={metrics['f1_weighted']:.4f}")
        if metrics["f1_macro"] > best_multi_f1:
            best_multi_f1 = metrics["f1_macro"]
            best_multi_name = name
            best_multi_model = model

    save_model(best_multi_model, out_dir / "multiclass_best.joblib")
    print(f"Best multiclass model: {best_multi_name}")

    # Final test evaluation with best models
    bin_test_pred = best_binary_model.predict(X_test)
    bin_test_proba = _predict_proba_pos(best_binary_model, X_test)
    multi_test_pred = best_multi_model.predict(X_test)

    report = {
        "selection_criteria": {
            "binary": "validation F1 (primary); PR-AUC, FPR, FNR reported for IDS imbalance analysis",
            "multiclass": "validation macro-F1",
        },
        "selected_features": bundle.selected_features,
        "binary": {
            "best": best_binary_name,
            "validation": binary_results,
            "test": evaluate_binary(y_bin_test, bin_test_pred, bin_test_proba),
        },
        "multiclass": {
            "best": best_multi_name,
            "classes": class_names,
            "validation": {k: {kk: vv for kk, vv in v.items() if kk != "report"} for k, v in multi_results.items()},
            "test": {
                k: v
                for k, v in evaluate_multiclass(y_multi_test, multi_test_pred, labels=class_names).items()
                if k != "report"
            },
        },
    }
    (out_dir / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Persist a small SHAP background sample
    import numpy as np

    bg_idx = np.random.RandomState(cfg["data"]["random_state"]).choice(len(X_train), size=min(200, len(X_train)), replace=False)
    np.save(out_dir / "shap_background.npy", X_train[bg_idx])
    print(f"\nArtifacts written to {out_dir}")
    print(json.dumps({"binary_test": report["binary"]["test"], "multiclass_test": report["multiclass"]["test"]}, indent=2))


if __name__ == "__main__":
    main()
