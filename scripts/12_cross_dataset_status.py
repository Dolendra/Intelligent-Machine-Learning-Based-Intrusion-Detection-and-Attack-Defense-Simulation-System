"""Cross-dataset evaluation against an external flow CSV directory.

If CSE-CIC-IDS2018 (or compatible) CSVs are present and share enough features with
the CICIDS2017-trained bundle, scores binary_best under distribution shift.
Otherwise writes an honest skipped / partial report.
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
from ml.evaluation.metrics import evaluate_binary
from ml.features.pipeline import FeatureBundle
from ml.models.factory import load_model
from ml.preprocessing.dataset import normalize_labels


def _strip(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    return df


def _load_external_sample(external: Path, max_rows: int = 50000) -> pd.DataFrame:
    frames = []
    remaining = max_rows
    for path in sorted(external.glob("*.csv")):
        if remaining <= 0:
            break
        chunk = pd.read_csv(path, low_memory=False, nrows=remaining)
        chunk = _strip(chunk)
        frames.append(chunk)
        remaining -= len(chunk)
    if not frames:
        raise FileNotFoundError("No CSV rows loaded")
    return pd.concat(frames, ignore_index=True)


def _prepare(df: pd.DataFrame, expected_features: list[str]) -> tuple[pd.DataFrame, np.ndarray | None, dict]:
    overlap = [c for c in expected_features if c in df.columns]
    missing = [c for c in expected_features if c not in df.columns]
    info = {
        "feature_overlap": len(overlap),
        "feature_expected": len(expected_features),
        "overlap_ratio": round(len(overlap) / max(1, len(expected_features)), 3),
        "missing_examples": missing[:12],
    }
    work = df.copy()
    for col in missing:
        work[col] = 0.0
    for col in expected_features:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.replace([np.inf, -np.inf], np.nan).dropna(subset=expected_features)
    y = None
    if "Label" in work.columns:
        labels = normalize_labels(work["Label"])
        y = (labels != "BENIGN").astype(int).to_numpy()
    return work[expected_features], y, info


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    external = Path(cfg.get("research", {}).get("external_dataset_dir", "CSE-CIC-IDS2018"))
    if not external.is_absolute():
        external = ROOT / external

    report: dict = {
        "experiment": "cross_dataset_validation",
        "train_dataset": "CICIDS2017",
        "external_dataset_dir": str(external),
        "status": "skipped",
        "reason": None,
        "metrics": None,
        "note": (
            "External generalization probe. Missing features are zero-filled and recorded — "
            "results under low overlap should be interpreted cautiously."
        ),
    }

    if not external.exists():
        report["reason"] = "External dataset directory not found"
    else:
        csvs = list(external.glob("*.csv"))
        report["csv_files_found"] = len(csvs)
        if not csvs:
            report["reason"] = "Directory exists but contains no CSV files"
        else:
            bundle_path = out_dir / "feature_bundle.joblib"
            model_path = out_dir / "binary_best.joblib"
            if not bundle_path.exists() or not model_path.exists():
                report["status"] = "ready_for_implementation"
                report["reason"] = "External CSVs found but trained CICIDS2017 models are missing"
            else:
                try:
                    raw = _load_external_sample(external)
                    bundle = FeatureBundle.load(bundle_path)
                    model = load_model(model_path)
                    X_df, y, info = _prepare(raw, list(bundle.feature_names))
                    report["schema"] = info
                    if info["overlap_ratio"] < 1.0:
                        report["status"] = "partial"
                        report["compatibility"] = "PARTIALLY_COMPATIBLE"
                        report["reason"] = (
                            f"Feature overlap {info['overlap_ratio']} < 1.0 — "
                            "missing features would require fabrication; official metrics withheld"
                        )
                    elif y is None:
                        report["status"] = "partial"
                        report["compatibility"] = "PARTIALLY_COMPATIBLE"
                        report["reason"] = "No Label column — cannot compute supervised metrics"
                    elif len(X_df) < 100:
                        report["status"] = "partial"
                        report["compatibility"] = "PARTIALLY_COMPATIBLE"
                        report["reason"] = "Too few usable external rows after cleaning"
                    else:
                        report["compatibility"] = "EXACT_COMPATIBLE"
                        X = bundle.transform(X_df, task="binary")
                        if hasattr(model, "predict_proba"):
                            proba = model.predict_proba(X)
                            p = proba[:, 1] if proba.shape[1] == 2 else proba.max(axis=1)
                        else:
                            p = model.predict(X).astype(float)
                        thr = float(cfg.get("models", {}).get("binary_threshold", 0.5))
                        pred = (p >= thr).astype(int)
                        metrics = evaluate_binary(y, pred, p)
                        report["status"] = "scored"
                        report["reason"] = None
                        report["n_scored"] = int(len(X_df))
                        report["metrics"] = {
                            k: metrics[k]
                            for k in ("precision", "recall", "f1", "pr_auc", "fpr", "fnr", "mcc")
                            if k in metrics
                        }
                except Exception as exc:  # noqa: BLE001
                    report["status"] = "error"
                    report["reason"] = str(exc)

    path = out_dir / "cross_dataset_status.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {path} status={report['status']}")


if __name__ == "__main__":
    main()
