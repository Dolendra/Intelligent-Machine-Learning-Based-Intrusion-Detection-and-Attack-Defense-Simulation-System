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
from ml.evaluation.selection import binary_selection_score, multiclass_selection_score
from ml.features.intensity import build_intensity_reference, save_intensity_reference
from ml.features.pipeline import fit_feature_pipeline, transform_attack_split, transform_split
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
    bundle, X_train, y_bin_train, _ = fit_feature_pipeline(train)
    X_val, y_bin_val, _ = transform_split(bundle, val, task="binary")
    X_test, y_bin_test, _ = transform_split(bundle, test, task="binary")
    X_train_m, y_multi_train, _ = transform_attack_split(bundle, train)
    X_val_m, y_multi_val, _ = transform_attack_split(bundle, val)
    X_test_m, y_multi_test, _ = transform_attack_split(bundle, test)
    bundle.save(out_dir / "feature_bundle.joblib")
    overlap = set(bundle.selected_features) & set(bundle.selected_features_multiclass)
    print(
        f"Selected {len(bundle.selected_features)} binary features; "
        f"{len(bundle.selected_features_multiclass)} multiclass features; "
        f"overlap={len(overlap)}; attack_classes={bundle.attack_class_names()}"
    )
    intensity_ref = build_intensity_reference(train)
    save_intensity_reference(intensity_ref, out_dir / "intensity_reference.json")
    print("Wrote intensity_reference.json (train percentiles)")

    binary_results = {}
    best_binary_name = None
    best_binary_score = -1.0
    best_binary_model = None
    selection_weights = cfg.get("models", {}).get("selection_weights")

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
        score = binary_selection_score(metrics, selection_weights)
        metrics["selection_score"] = round(score, 6)
        binary_results[name] = metrics
        pr = metrics.get("pr_auc")
        pr_s = f"{pr:.4f}" if pr is not None else "n/a"
        print(
            f"  {name}: score={score:.4f} F1={metrics['f1']:.4f} recall={metrics['recall']:.4f} "
            f"PR-AUC={pr_s} FPR={metrics['fpr']:.4f}"
        )
        if score > best_binary_score:
            best_binary_score = score
            best_binary_name = name
            best_binary_model = model

    save_model(best_binary_model, out_dir / "binary_best.joblib")
    print(f"Best binary model: {best_binary_name} (multi-objective selection_score={best_binary_score:.4f})")

    multi_results = {}
    best_multi_name = None
    best_multi_f1 = -1.0
    best_multi_model = None
    class_names = bundle.attack_class_names()

    print("\n=== Stage 2: Attack-family classification (attack rows only) ===")
    for name in cfg["models"]["multiclass"]["algorithms"]:
        model = build_model(name, cfg["data"]["random_state"])
        t0 = time.perf_counter()
        model.fit(X_train_m, y_multi_train)
        train_time = time.perf_counter() - t0
        pred = model.predict(X_val_m)
        metrics = evaluate_multiclass(y_multi_val, pred, labels=class_names)
        metrics["train_seconds"] = round(train_time, 3)
        multi_results[name] = {k: v for k, v in metrics.items() if k != "report"}
        multi_results[name]["report"] = metrics["report"]
        score = multiclass_selection_score(metrics)
        multi_results[name]["selection_score"] = round(score, 6)
        print(
            f"  {name}: score={score:.4f} macro-F1={metrics['f1_macro']:.4f} "
            f"weighted-F1={metrics['f1_weighted']:.4f}"
        )
        if score > best_multi_f1:
            best_multi_f1 = score
            best_multi_name = name
            best_multi_model = model

    save_model(best_multi_model, out_dir / "multiclass_best.joblib")
    print(f"Best multiclass model: {best_multi_name}")

    bin_test_pred = best_binary_model.predict(X_test)
    bin_test_proba = _predict_proba_pos(best_binary_model, X_test)
    multi_test_pred = best_multi_model.predict(X_test_m)

    report = {
        "selection_criteria": {
            "binary": "multi-objective: recall/F1/PR-AUC/FPR/latency (see models.selection_weights)",
            "multiclass": "0.7*macro-F1 + 0.3*weighted-F1 on attack-only rows",
            "features": "dual SelectKBest (binary vs multiclass) when features.dual_selectors=true",
            "stage2": "attack_label_encoder excludes BENIGN",
        },
        "selected_features": bundle.selected_features,
        "selected_features_multiclass": bundle.selected_features_multiclass,
        "feature_overlap": sorted(set(bundle.selected_features) & set(bundle.selected_features_multiclass)),
        "binary": {
            "best": best_binary_name,
            "validation": binary_results,
            "test": evaluate_binary(y_bin_test, bin_test_pred, bin_test_proba),
        },
        "multiclass": {
            "best": best_multi_name,
            "classes": class_names,
            "n_train_attack": int(len(y_multi_train)),
            "n_val_attack": int(len(y_multi_val)),
            "n_test_attack": int(len(y_multi_test)),
            "validation": {k: {kk: vv for kk, vv in v.items() if kk != "report"} for k, v in multi_results.items()},
            "test": {
                k: v
                for k, v in evaluate_multiclass(y_multi_test, multi_test_pred, labels=class_names).items()
                if k != "report"
            },
        },
    }
    (out_dir / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    import numpy as np

    bg_idx = np.random.RandomState(cfg["data"]["random_state"]).choice(
        len(X_train), size=min(200, len(X_train)), replace=False
    )
    np.save(out_dir / "shap_background.npy", X_train[bg_idx])

    import importlib.util

    meta_path = ROOT / "scripts" / "13_write_model_metadata.py"
    spec = importlib.util.spec_from_file_location("write_model_metadata", meta_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        meta = mod.build_metadata()
        (out_dir / "model_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"\nArtifacts written to {out_dir}")
    print(
        json.dumps(
            {"binary_test": report["binary"]["test"], "multiclass_test": report["multiclass"]["test"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
