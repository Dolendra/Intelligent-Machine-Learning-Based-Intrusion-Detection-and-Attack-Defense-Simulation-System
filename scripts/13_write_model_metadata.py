"""Enhance model_metadata.json with reproducibility fields."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path


def _pkg_ver(name: str) -> str | None:
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", None)
    except Exception:
        return None


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _git_commit() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return None


def _config_hash() -> str:
    cfg_path = ROOT / "config.yaml"
    return _file_sha256(cfg_path) or "n/a"


def build_metadata() -> dict:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    report_path = out_dir / "training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    op_path = out_dir / "threshold_operating_point.json"
    operating = json.loads(op_path.read_text(encoding="utf-8")) if op_path.exists() else {}

    binary = report.get("binary", {})
    multi = report.get("multiclass", {})
    test_bin = binary.get("test", {})
    processed = resolve_path(cfg["data"]["processed_dir"])
    meta_path = processed / "meta.json"
    split_meta = {}
    if meta_path.exists():
        try:
            split_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            split_meta = {}

    meta = {
        "application_version": cfg["project"]["version"],
        "model_version": cfg.get("models", {}).get("model_version", "1.0.0"),
        "dataset": "CICIDS2017",
        "dataset_source": cfg["data"]["raw_dir"],
        "sample_frac": cfg["data"].get("sample_frac"),
        "random_state": cfg["data"].get("random_state"),
        "min_class_count": cfg["data"].get("min_class_count"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "training_git_commit": _git_commit(),
        "config_hash": _config_hash(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {
            "scikit-learn": _pkg_ver("sklearn"),
            "xgboost": _pkg_ver("xgboost"),
            "shap": _pkg_ver("shap"),
            "numpy": _pkg_ver("numpy"),
            "pandas": _pkg_ver("pandas"),
        },
        "split_sizes": {
            "training_rows": split_meta.get("n_train"),
            "validation_rows": split_meta.get("n_val"),
            "test_rows": split_meta.get("n_test"),
        },
        "binary_model": binary.get("best"),
        "multiclass_model": multi.get("best"),
        "attack_classes": multi.get("classes") or [],
        "feature_count_binary": len(report.get("selected_features") or []),
        "feature_count_multiclass": len(
            report.get("selected_features_multiclass") or report.get("selected_features") or []
        ),
        "dual_selectors": bool(cfg.get("features", {}).get("dual_selectors", False)),
        "binary_threshold": operating.get("operating_threshold", cfg.get("models", {}).get("binary_threshold", 0.5)),
        "uncertainty_lower": operating.get(
            "uncertainty_lower", cfg.get("models", {}).get("uncertainty_lower", 0.30)
        ),
        "uncertainty_upper": operating.get(
            "uncertainty_upper", cfg.get("models", {}).get("uncertainty_upper", 0.70)
        ),
        "use_calibrated_binary": bool(cfg.get("models", {}).get("use_calibrated_binary", False)),
        "test_metrics_binary": {
            "f1": test_bin.get("f1"),
            "recall": test_bin.get("recall"),
            "precision": test_bin.get("precision"),
            "pr_auc": test_bin.get("pr_auc"),
            "fpr": test_bin.get("fpr"),
            "fnr": test_bin.get("fnr"),
            "brier_score": test_bin.get("brier_score"),
            "ece": test_bin.get("ece"),
        },
        "artifact_hashes": {
            "binary_best": _file_sha256(out_dir / "binary_best.joblib"),
            "multiclass_best": _file_sha256(out_dir / "multiclass_best.joblib"),
            "feature_bundle": _file_sha256(out_dir / "feature_bundle.joblib"),
            "binary_calibrated": _file_sha256(out_dir / "binary_calibrated.joblib"),
            "processed_train": _file_sha256(processed / "train.parquet"),
        },
        "notes": [
            "Metadata for reproducibility — not a claim of production SOC deployment.",
            "Stage-2 multiclass excludes BENIGN (attack_label_encoder).",
            "Calibration wrapper is optional; enable models.use_calibrated_binary after script 14 if justified.",
        ],
    }
    return meta


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = build_metadata()
    path = out_dir / "model_metadata.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    print(json.dumps({"binary_model": meta["binary_model"], "git": meta["training_git_commit"]}, indent=2))


if __name__ == "__main__":
    main()
