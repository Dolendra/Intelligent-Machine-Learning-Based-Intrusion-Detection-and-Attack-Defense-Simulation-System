"""Threshold sweep experiment for binary IDS operating point."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from ids_config import load_config, resolve_path
from ml.evaluation.metrics import evaluate_binary
from ml.features.pipeline import FeatureBundle, transform_split
from ml.models.factory import load_model
from ml.preprocessing.dataset import load_processed


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    bundle = FeatureBundle.load(out_dir / "feature_bundle.joblib")
    model = load_model(out_dir / "binary_best.joblib")
    val = load_processed("val")
    # Cap for speed if huge
    if len(val) > 150000:
        val = val.sample(n=150000, random_state=cfg["data"]["random_state"])
    X, y, _ = transform_split(bundle, val, task="binary")
    if not hasattr(model, "predict_proba"):
        raise SystemExit("Binary model lacks predict_proba")
    proba = model.predict_proba(X)
    # attack class index
    classes = list(getattr(model, "classes_", [0, 1]))
    idx = classes.index(1) if 1 in classes else 1
    p = proba[:, idx]

    rows = []
    for thr in [round(x, 2) for x in np.arange(0.10, 0.95, 0.05)]:
        pred = (p >= thr).astype(int)
        m = evaluate_binary(y, pred, p)
        rows.append(
            {
                "threshold": thr,
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "fpr": m["fpr"],
                "fnr": m["fnr"],
                "pr_auc": m.get("pr_auc"),
            }
        )

    # Suggest threshold: maximize F1 among candidates with recall >= 0.95 if possible
    eligible = [r for r in rows if r["recall"] >= 0.95] or rows
    best = max(eligible, key=lambda r: (r["f1"], -r["fpr"]))
    # Uncertainty band heuristic from sweep: low = thr where FPR spikes down, high = thr for high precision
    uncertain_low = 0.30
    uncertain_high = 0.70
    report = {
        "experiment": "binary_threshold_sweep",
        "val_rows": int(len(val)),
        "suggested_threshold": best["threshold"],
        "suggested_reason": "Max F1 among thresholds with recall>=0.95 when available; else max F1",
        "current_config_threshold": cfg.get("models", {}).get("binary_threshold", 0.5),
        "certainty_bands_project_default": {"likely_benign_lt": uncertain_low, "likely_attack_gt": uncertain_high},
        "sweep": rows,
        "note": "Experiment on validation sample/slice — update config.yaml binary_threshold after review.",
    }
    path = out_dir / "threshold_sweep.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    print(f"Suggested threshold={best['threshold']} F1={best['f1']:.4f} Recall={best['recall']:.4f} FPR={best['fpr']:.4f}")


if __name__ == "__main__":
    main()
