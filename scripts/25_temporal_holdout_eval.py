"""Day-aware / temporal holdout scoring of the frozen IDS models.

Uses CICIDS2017 MachineLearningCVE day-named CSVs when present:
  Train proxy → Mon–Thu samples
  Temporal test → Friday samples

Compares against the recorded IID stratified test metrics from training_report.json.

This does **not** retrain; it scores the freeze joblibs under a temporal slice.
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
from ml.features.pipeline import FeatureBundle, transform_attack_split
from ml.models.factory import load_model
from ml.preprocessing.dataset import clean_dataframe, list_csv_files, normalize_labels


def _day_from_name(path: Path) -> str:
    name = path.name.lower()
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday"):
        if name.startswith(day):
            return day.capitalize()
    return "Unknown"


def _sample_csv(path: Path, n: int, seed: int) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    df = clean_dataframe(df)
    if "Label" not in df.columns:
        return pd.DataFrame()
    df["Label"] = normalize_labels(df["Label"])
    df["is_attack"] = (df["Label"] != "BENIGN").astype(int)
    df["source_day"] = _day_from_name(path)
    if len(df) > n:
        df = df.sample(n=n, random_state=seed)
    return df


def _proba_attack(model, X: np.ndarray) -> np.ndarray:
    p = model.predict_proba(X)
    classes = list(getattr(model, "classes_", [0, 1]))
    idx = classes.index(1) if 1 in classes else 1
    return p[:, idx]


def main() -> None:
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    seed = int(cfg["data"]["random_state"])
    per_file = int(cfg.get("research", {}).get("temporal_sample_per_file", 12000))
    threshold = float(cfg["models"].get("binary_threshold", 0.85))
    op = out_dir / "threshold_operating_point.json"
    if op.exists():
        threshold = float(json.loads(op.read_text(encoding="utf-8")).get("operating_threshold", threshold))

    report: dict = {
        "experiment": "temporal_day_holdout",
        "status": "ok",
        "note": (
            "Scores frozen joblibs on day-aware CSV samples. "
            "IID metrics are copied from training_report for comparison. "
            "This is deployment-domain style validation, not a claim of production drift absence."
        ),
        "operating_threshold": threshold,
    }

    try:
        files = list_csv_files()
    except Exception as exc:  # noqa: BLE001
        report["status"] = "skipped"
        report["reason"] = f"Raw MachineLearningCVE unavailable: {exc}"
        path = out_dir / "temporal_holdout_report.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"wrote": str(path), "status": report["status"]}, indent=2))
        return

    frames = []
    for path in files:
        try:
            part = _sample_csv(path, per_file, seed)
            if not part.empty:
                frames.append(part)
                print(f"Sampled {len(part)} from {path.name} ({_day_from_name(path)})")
        except Exception as exc:  # noqa: BLE001
            print(f"Skip {path.name}: {exc}")

    if not frames:
        report["status"] = "skipped"
        report["reason"] = "No usable CSV samples"
    else:
        data = pd.concat(frames, ignore_index=True)
        train_days = {"Monday", "Tuesday", "Wednesday", "Thursday"}
        temporal = data[data["source_day"] == "Friday"].reset_index(drop=True)
        # Also score a stratified IID-like subsample from Mon–Thu for local reference
        early = data[data["source_day"].isin(train_days)].reset_index(drop=True)

        bundle = FeatureBundle.load(out_dir / "feature_bundle.joblib")
        binary = load_model(out_dir / "binary_best.joblib")
        multi = load_model(out_dir / "multiclass_best.joblib")

        def score_binary(df: pd.DataFrame) -> dict:
            if len(df) < 50:
                return {"n": len(df), "skipped": True}
            X = bundle.transform(df, task="binary")
            y = df["is_attack"].to_numpy()
            proba = _proba_attack(binary, X)
            pred = (proba >= threshold).astype(int)
            m = evaluate_binary(y, pred, proba)
            m["n"] = int(len(df))
            m["attack_rate"] = float(y.mean())
            return m

        def score_multi(df: pd.DataFrame) -> dict:
            attacks = df[df["is_attack"] == 1]
            if len(attacks) < 30:
                return {"n": len(attacks), "skipped": True}
            try:
                X, y, _ = transform_attack_split(bundle, attacks)
            except Exception as exc:  # noqa: BLE001
                return {"n": len(attacks), "skipped": True, "reason": str(exc)}
            pred = multi.predict(X)
            m = evaluate_multiclass(y, pred)
            m["n"] = int(len(attacks))
            return m

        report["days_present"] = sorted(data["source_day"].dropna().unique().tolist())
        report["samples"] = {
            "early_mon_thu": int(len(early)),
            "friday_temporal": int(len(temporal)),
            "per_file_cap": per_file,
        }
        report["early_mon_thu"] = {"binary": score_binary(early), "multiclass": score_multi(early)}
        report["friday_temporal_holdout"] = {
            "binary": score_binary(temporal),
            "multiclass": score_multi(temporal),
        }

        tr = out_dir / "training_report.json"
        if tr.exists():
            training = json.loads(tr.read_text(encoding="utf-8"))
            report["iid_stratified_from_training_report"] = {
                "binary_test": training.get("binary", {}).get("test"),
                "multiclass_test": {
                    k: v
                    for k, v in (training.get("multiclass", {}).get("test") or {}).items()
                    if k != "confusion_matrix"
                },
            }

        fri_bin = report["friday_temporal_holdout"]["binary"]
        iid_bin = (report.get("iid_stratified_from_training_report") or {}).get("binary_test") or {}
        report["interpretation"] = (
            "Compare friday_temporal_holdout.binary with iid_stratified_from_training_report.binary_test. "
            "A drop under day/scenario holdout indicates limited generalization beyond the stratified IID split "
            "and should be discussed honestly in the report/viva."
        )
        if isinstance(fri_bin, dict) and iid_bin and not fri_bin.get("skipped"):
            report["delta_f1_iid_minus_friday"] = round(
                float(iid_bin.get("f1", 0) or 0) - float(fri_bin.get("f1", 0) or 0), 4
            )

    path = out_dir / "temporal_holdout_report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(path), "status": report["status"]}, indent=2))


if __name__ == "__main__":
    main()
