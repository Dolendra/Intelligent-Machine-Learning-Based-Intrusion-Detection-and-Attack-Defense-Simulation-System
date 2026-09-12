"""Calibration + constrained HPO research experiment (sample-based, not full retrain).

Writes:
  models/trained_models/calibration_hpo_experiment.json
  models/trained_models/figures/calibration_curve.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV

from ids_config import load_config, resolve_path
from ml.evaluation.calibration import calibration_report
from ml.evaluation.metrics import evaluate_binary
from ml.features.pipeline import fit_feature_pipeline, transform_split
from ml.preprocessing.dataset import load_processed


def _sample(df, n: int, seed: int):
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed)


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    seed = int(cfg["data"]["random_state"])
    sample_n = int(cfg.get("research", {}).get("experiment_sample_rows", 60000))
    n_iter = int(cfg.get("research", {}).get("hpo_n_iter", 8))

    print("Loading sampled train/val…")
    train = _sample(load_processed("train"), sample_n, seed)
    val = _sample(load_processed("val"), max(8000, sample_n // 6), seed)

    bundle, X_tr, y_tr, _ = fit_feature_pipeline(train, dual_selectors=False)
    X_va, y_va, _ = transform_split(bundle, val, task="binary")

    base = RandomForestClassifier(
        n_estimators=80,
        max_depth=20,
        n_jobs=-1,
        class_weight="balanced_subsample",
        random_state=seed,
    )
    t0 = time.perf_counter()
    base.fit(X_tr, y_tr)
    base_time = time.perf_counter() - t0
    base_proba = base.predict_proba(X_va)[:, 1]
    base_pred = (base_proba >= 0.5).astype(int)
    base_metrics = evaluate_binary(y_va, base_pred, base_proba)
    base_cal = calibration_report(y_va, base_proba)

    print("Calibrating with isotonic CalibratedClassifierCV…")
    calibrated = CalibratedClassifierCV(base, method="isotonic", cv=3)
    # Fit calibration on a slice of train to keep runtime bounded
    cal_n = min(25000, len(X_tr))
    idx = np.random.RandomState(seed).choice(len(X_tr), size=cal_n, replace=False)
    t0 = time.perf_counter()
    calibrated.fit(X_tr[idx], y_tr[idx])
    cal_time = time.perf_counter() - t0
    cal_proba = calibrated.predict_proba(X_va)[:, 1]
    cal_pred = (cal_proba >= 0.5).astype(int)
    cal_metrics = evaluate_binary(y_va, cal_pred, cal_proba)
    cal_cal = calibration_report(y_va, cal_proba)

    print(f"Constrained RandomizedSearchCV (n_iter={n_iter})…")
    search = RandomizedSearchCV(
        RandomForestClassifier(n_jobs=-1, class_weight="balanced_subsample", random_state=seed),
        param_distributions={
            "n_estimators": [60, 80, 120],
            "max_depth": [12, 16, 20, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "max_features": ["sqrt", 0.5],
        },
        n_iter=n_iter,
        scoring="f1",
        cv=3,
        random_state=seed,
        n_jobs=-1,
        refit=True,
    )
    hpo_n = min(30000, len(X_tr))
    hpo_idx = np.random.RandomState(seed + 1).choice(len(X_tr), size=hpo_n, replace=False)
    t0 = time.perf_counter()
    search.fit(X_tr[hpo_idx], y_tr[hpo_idx])
    hpo_time = time.perf_counter() - t0
    hpo_proba = search.best_estimator_.predict_proba(X_va)[:, 1]
    hpo_pred = (hpo_proba >= 0.5).astype(int)
    hpo_metrics = evaluate_binary(y_va, hpo_pred, hpo_proba)
    hpo_cal = calibration_report(y_va, hpo_proba)

    # Reliability plot
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0, 1], [0, 1], "k--", label="Perfect")
    for label, report in (("Baseline RF", base_cal), ("Isotonic calibrated", cal_cal), ("HPO RF", hpo_cal)):
        curve = report.get("reliability_curve")
        if not curve:
            continue
        ax.plot(curve["mean_predicted_value"], curve["fraction_of_positives"], marker="o", label=label)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Calibration curves (validation sample)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig_path = fig_dir / "calibration_curve.png"
    fig.savefig(fig_path, dpi=140)
    plt.close(fig)

    report = {
        "experiment": "calibration_and_constrained_hpo",
        "sample_train_rows": int(len(train)),
        "sample_val_rows": int(len(val)),
        "baseline": {
            "metrics": {k: v for k, v in base_metrics.items() if k != "confusion_matrix"},
            "calibration": {k: v for k, v in base_cal.items() if k != "reliability_curve"},
            "fit_seconds": round(base_time, 2),
        },
        "isotonic_calibrated": {
            "metrics": {k: v for k, v in cal_metrics.items() if k != "confusion_matrix"},
            "calibration": {k: v for k, v in cal_cal.items() if k != "reliability_curve"},
            "fit_seconds": round(cal_time, 2),
        },
        "randomized_search": {
            "best_params": search.best_params_,
            "best_cv_f1": float(search.best_score_),
            "metrics": {k: v for k, v in hpo_metrics.items() if k != "confusion_matrix"},
            "calibration": {k: v for k, v in hpo_cal.items() if k != "reliability_curve"},
            "fit_seconds": round(hpo_time, 2),
            "n_iter": n_iter,
        },
        "figures": {"calibration_curve": str(fig_path.relative_to(ROOT))},
        "note": (
            "Sample-based research experiment. Does not replace production joblibs. "
            "Confidence ≠ empirical probability until calibration is validated."
        ),
    }
    out_path = out_dir / "calibration_hpo_experiment.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        f"Brier baseline={base_cal['brier_score']:.4f} calibrated={cal_cal['brier_score']:.4f} | "
        f"ECE {base_cal['ece']:.4f} -> {cal_cal['ece']:.4f} | "
        f"HPO val F1={hpo_metrics['f1']:.4f} params={search.best_params_}"
    )


if __name__ == "__main__":
    main()
