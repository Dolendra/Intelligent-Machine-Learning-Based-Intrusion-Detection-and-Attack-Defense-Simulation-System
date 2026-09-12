"""Fit an optional isotonic-calibrated binary wrapper (sample-based, additive artifact).

Saves models/trained_models/binary_calibrated.joblib
Does not replace binary_best.joblib. Enable via config:
  models.use_calibrated_binary: true
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from sklearn.calibration import CalibratedClassifierCV

from ids_config import load_config, resolve_path
from ml.evaluation.calibration import calibration_report
from ml.evaluation.metrics import evaluate_binary
from ml.features.pipeline import FeatureBundle, transform_split
from ml.models.factory import load_model, save_model
from ml.preprocessing.dataset import load_processed


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    seed = int(cfg["data"]["random_state"])
    sample_n = int(cfg.get("research", {}).get("calibration_fit_rows", 40000))

    bundle = FeatureBundle.load(out_dir / "feature_bundle.joblib")
    base = load_model(out_dir / "binary_best.joblib")

    print("Loading calibration fit/val samples…")
    train = load_processed("train")
    val = load_processed("val")
    if len(train) > sample_n:
        train = train.sample(n=sample_n, random_state=seed)
    if len(val) > max(8000, sample_n // 5):
        val = val.sample(n=max(8000, sample_n // 5), random_state=seed)

    X_tr, y_tr, _ = transform_split(bundle, train, task="binary")
    X_va, y_va, _ = transform_split(bundle, val, task="binary")

    # Prefer cv='prefit' when base is already trained (sklearn API)
    try:
        calibrated = CalibratedClassifierCV(base, method="isotonic", cv="prefit")
        t0 = time.perf_counter()
        calibrated.fit(X_tr, y_tr)
        fit_s = time.perf_counter() - t0
    except Exception:
        calibrated = CalibratedClassifierCV(estimator=base, method="isotonic", cv=3)
        t0 = time.perf_counter()
        calibrated.fit(X_tr, y_tr)
        fit_s = time.perf_counter() - t0

    before = base.predict_proba(X_va)[:, 1]
    after = calibrated.predict_proba(X_va)[:, 1]
    report = {
        "fit_seconds": round(fit_s, 2),
        "sample_train_rows": int(len(train)),
        "sample_val_rows": int(len(val)),
        "before": {
            "metrics": {
                k: v
                for k, v in evaluate_binary(y_va, (before >= 0.5).astype(int), before).items()
                if k != "confusion_matrix"
            },
            "calibration": {k: v for k, v in calibration_report(y_va, before).items() if k != "reliability_curve"},
        },
        "after": {
            "metrics": {
                k: v
                for k, v in evaluate_binary(y_va, (after >= 0.5).astype(int), after).items()
                if k != "confusion_matrix"
            },
            "calibration": {k: v for k, v in calibration_report(y_va, after).items() if k != "reliability_curve"},
        },
        "enable_with": "models.use_calibrated_binary: true",
        "note": "Additive calibrated wrapper — production default remains binary_best unless enabled.",
    }
    save_model(calibrated, out_dir / "binary_calibrated.joblib")
    (out_dir / "calibration_wrapper_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_dir / 'binary_calibrated.joblib'}")
    print(
        f"Brier {report['before']['calibration']['brier_score']:.4f} → {report['after']['calibration']['brier_score']:.4f} | "
        f"ECE {report['before']['calibration']['ece']:.4f} → {report['after']['calibration']['ece']:.4f}"
    )


if __name__ == "__main__":
    main()
