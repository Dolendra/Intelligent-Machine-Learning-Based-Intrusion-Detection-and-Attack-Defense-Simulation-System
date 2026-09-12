"""Compare shared vs dual (binary/multiclass) feature selection — research experiment.

Does not replace production models. Writes a JSON report under models/trained_models/.
Uses a stratified sample of the training split for speed.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sklearn.ensemble import RandomForestClassifier

from ids_config import load_config, resolve_path
from ml.evaluation.metrics import evaluate_binary, evaluate_multiclass
from ml.features.pipeline import fit_feature_pipeline, transform_split
from ml.preprocessing.dataset import load_processed


def _sample(df, n: int, seed: int):
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed)


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    seed = int(cfg["data"]["random_state"])
    sample_n = int(cfg.get("features", {}).get("experiment_sample_rows", 80000))

    print("Loading processed train/val…")
    train = _sample(load_processed("train"), sample_n, seed)
    val = _sample(load_processed("val"), max(10000, sample_n // 5), seed)

    print("Fitting SHARED selector (binary target only)…")
    shared, X_tr_s, yb_tr, ym_tr = fit_feature_pipeline(train, dual_selectors=False)
    X_va_s, yb_va, ym_va = transform_split(shared, val, task="binary")

    print("Fitting DUAL selectors…")
    dual, X_tr_b, yb_tr_d, ym_tr_d = fit_feature_pipeline(train, dual_selectors=True)
    X_va_b, yb_va_d, _ = transform_split(dual, val, task="binary")
    X_tr_m, _, ym_tr_dm = transform_split(dual, train, task="multiclass")
    X_va_m, _, ym_va_d = transform_split(dual, val, task="multiclass")

    rf = dict(n_estimators=60, max_depth=16, n_jobs=-1, random_state=seed)

    t0 = time.perf_counter()
    bin_shared = RandomForestClassifier(**rf).fit(X_tr_s, yb_tr)
    multi_shared = RandomForestClassifier(**rf).fit(X_tr_s, ym_tr)
    t_shared = time.perf_counter() - t0

    t0 = time.perf_counter()
    bin_dual = RandomForestClassifier(**rf).fit(X_tr_b, yb_tr_d)
    multi_dual = RandomForestClassifier(**rf).fit(X_tr_m, ym_tr_dm)
    t_dual = time.perf_counter() - t0

    classes = list(dual.label_encoder.classes_)
    report = {
        "experiment": "shared_vs_dual_feature_selection",
        "sample_train_rows": len(train),
        "sample_val_rows": len(val),
        "max_features": cfg["features"]["max_features"],
        "shared": {
            "binary_features": shared.selected_features,
            "binary_val": evaluate_binary(yb_va, bin_shared.predict(X_va_s), bin_shared.predict_proba(X_va_s)[:, 1]),
            "multiclass_val": {
                k: v
                for k, v in evaluate_multiclass(ym_va, multi_shared.predict(X_va_s), labels=classes).items()
                if k != "report"
            },
            "train_seconds": round(t_shared, 2),
        },
        "dual": {
            "binary_features": dual.selected_features,
            "multiclass_features": dual.selected_features_multiclass,
            "overlap": sorted(set(dual.selected_features) & set(dual.selected_features_multiclass)),
            "binary_only": sorted(set(dual.selected_features) - set(dual.selected_features_multiclass)),
            "multiclass_only": sorted(set(dual.selected_features_multiclass) - set(dual.selected_features)),
            "binary_val": evaluate_binary(yb_va_d, bin_dual.predict(X_va_b), bin_dual.predict_proba(X_va_b)[:, 1]),
            "multiclass_val": {
                k: v
                for k, v in evaluate_multiclass(ym_va_d, multi_dual.predict(X_va_m), labels=classes).items()
                if k != "report"
            },
            "train_seconds": round(t_dual, 2),
        },
        "note": (
            "Research experiment on a sample — not a replacement for full-dataset production artifacts. "
            "Re-run scripts/02_train_models.py to train production models with dual selectors."
        ),
    }
    # Drop large confusion matrices from printed summary friendliness — keep in file
    path = out_dir / "feature_selector_experiment.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    print(
        "Shared binary F1={:.4f} macro-F1={:.4f} | Dual binary F1={:.4f} macro-F1={:.4f} | overlap={}".format(
            report["shared"]["binary_val"]["f1"],
            report["shared"]["multiclass_val"]["f1_macro"],
            report["dual"]["binary_val"]["f1"],
            report["dual"]["multiclass_val"]["f1_macro"],
            len(report["dual"]["overlap"]),
        )
    )


if __name__ == "__main__":
    main()
