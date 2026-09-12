"""Write / refresh model_metadata.json from training artifacts (no retrain required)."""
from __future__ import annotations

import hashlib
import json
import platform
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


def build_metadata() -> dict:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    report_path = out_dir / "training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}

    binary = report.get("binary", {})
    multi = report.get("multiclass", {})
    test_bin = binary.get("test", {})

    meta = {
        "application_version": cfg["project"]["version"],
        "model_version": cfg.get("models", {}).get("model_version", "1.0.0"),
        "dataset": "CICIDS2017",
        "dataset_source": cfg["data"]["raw_dir"],
        "sample_frac": cfg["data"].get("sample_frac"),
        "random_state": cfg["data"].get("random_state"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {
            "scikit-learn": _pkg_ver("sklearn"),
            "xgboost": _pkg_ver("xgboost"),
            "shap": _pkg_ver("shap"),
            "numpy": _pkg_ver("numpy"),
            "pandas": _pkg_ver("pandas"),
        },
        "binary_model": binary.get("best"),
        "multiclass_model": multi.get("best"),
        "feature_count_binary": len(report.get("selected_features") or []),
        "feature_count_multiclass": len(report.get("selected_features_multiclass") or report.get("selected_features") or []),
        "dual_selectors": bool(cfg.get("features", {}).get("dual_selectors", False)),
        "binary_threshold": cfg.get("models", {}).get("binary_threshold", 0.5),
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
        },
        "notes": [
            "Metadata for reproducibility — not a claim of production SOC deployment.",
            "Calibration wrapper is optional; enable models.use_calibrated_binary after fitting script 14.",
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
    print(json.dumps({"binary_model": meta["binary_model"], "model_version": meta["model_version"]}, indent=2))


if __name__ == "__main__":
    main()
