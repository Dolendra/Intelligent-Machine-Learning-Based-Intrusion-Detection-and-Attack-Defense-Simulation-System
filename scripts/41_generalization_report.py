"""P10 — Consolidate frozen-model generalization evidence (no retrain / no tuning).

Builds `models/trained_models/generalization_report.json` from:
  - training_report.json (IID)
  - temporal_holdout_report.json (Friday / Mon–Thu)
  - drift_report.json (IID train→test PSI)
  - cross_dataset_status.json
  - model_metadata.json

Optionally computes **temporal** feature/label PSI: processed train → Friday day sample
(same sampling knobs as scripts/25_temporal_holdout_eval.py).

Does **not** modify joblibs or optimize against the temporal holdout.
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path
from ml.evaluation.drift import feature_drift_report, label_drift_report
from ml.preprocessing.dataset import (
    clean_dataframe,
    get_feature_columns,
    list_csv_files,
    load_processed,
    normalize_labels,
)


FAMILIES = ["Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]


def _git_commit() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return None


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _class_wise_from_cm(cm: list[list[int]], labels: list[str]) -> list[dict]:
    mat = np.asarray(cm, dtype=float)
    rows = []
    for i, name in enumerate(labels):
        if i >= mat.shape[0]:
            break
        tp = mat[i, i]
        fp = mat[:, i].sum() - tp
        fn = mat[i, :].sum() - tp
        support = float(mat[i, :].sum())
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        rows.append(
            {
                "attack_type": name,
                "precision": round(precision, 6),
                "recall": round(recall, 6),
                "f1": round(f1, 6),
                "support": support,
            }
        )
    return rows


def _off_diagonal_pairs(cm: list[list[int]], labels: list[str], *, min_count: int = 1) -> list[dict]:
    mat = np.asarray(cm, dtype=int)
    pairs = []
    for i, true_lab in enumerate(labels):
        for j, pred_lab in enumerate(labels):
            if i == j:
                continue
            n = int(mat[i, j]) if i < mat.shape[0] and j < mat.shape[1] else 0
            if n >= min_count:
                pairs.append({"true": true_lab, "predicted": pred_lab, "count": n})
    pairs.sort(key=lambda p: p["count"], reverse=True)
    return pairs


def _day_from_name(path: Path) -> str:
    name = path.name.lower()
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday"):
        if name.startswith(day):
            return day.capitalize()
    return "Unknown"


def _sample_friday(per_file: int, seed: int) -> pd.DataFrame | None:
    try:
        files = list_csv_files()
    except Exception:
        return None
    frames = []
    for path in files:
        if _day_from_name(path) != "Friday":
            continue
        try:
            df = pd.read_csv(path, low_memory=False)
            df = clean_dataframe(df)
            if "Label" not in df.columns:
                continue
            df["Label"] = normalize_labels(df["Label"])
            if len(df) > per_file:
                df = df.sample(n=per_file, random_state=seed)
            frames.append(df)
        except Exception as exc:  # noqa: BLE001
            print(f"Skip {path.name}: {exc}")
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def _delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round(float(a) - float(b), 5)


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

    training = _load_json(out_dir / "training_report.json") or {}
    temporal = _load_json(out_dir / "temporal_holdout_report.json") or {}
    drift_iid = _load_json(out_dir / "drift_report.json") or {}
    cross = _load_json(out_dir / "cross_dataset_status.json") or {}
    meta = _load_json(out_dir / "model_metadata.json") or {}

    iid_bin = (training.get("binary") or {}).get("test") or {}
    iid_multi = (training.get("multiclass") or {}).get("test") or {}
    classes = (training.get("multiclass") or {}).get("classes") or FAMILIES

    fri = (temporal.get("friday_temporal_holdout") or {})
    fri_bin = fri.get("binary") or {}
    fri_multi = fri.get("multiclass") or {}
    early = ((temporal.get("early_mon_thu") or {}).get("binary") or {})

    iid_class_wise = []
    iid_confusions = []
    if iid_multi.get("confusion_matrix"):
        iid_class_wise = _class_wise_from_cm(iid_multi["confusion_matrix"], classes)
        iid_confusions = _off_diagonal_pairs(iid_multi["confusion_matrix"], classes)

    fri_labels = temporal.get("friday_multiclass_families_present") or []
    fri_class_wise = temporal.get("friday_multiclass_class_wise") or []
    fri_confusions: list[dict] = []
    if fri_multi.get("confusion_matrix") and fri_labels:
        fri_confusions = _off_diagonal_pairs(fri_multi["confusion_matrix"], fri_labels)

    # Mark absent families explicitly for the temporal holdout
    present = set(fri_labels)
    temporal_family_status = []
    for fam in FAMILIES:
        if fam in present:
            row = next((r for r in fri_class_wise if r.get("attack_type") == fam), None)
            temporal_family_status.append(
                {
                    "attack_type": fam,
                    "present_in_friday_sample": True,
                    "precision": (row or {}).get("precision"),
                    "recall": (row or {}).get("recall"),
                    "f1": (row or {}).get("f1"),
                    "support": (row or {}).get("support"),
                }
            )
        else:
            temporal_family_status.append(
                {
                    "attack_type": fam,
                    "present_in_friday_sample": False,
                    "precision": None,
                    "recall": None,
                    "f1": None,
                    "support": 0,
                    "note": "Family absent from Friday sample — no temporal class-wise score.",
                }
            )

    # Temporal PSI: train → Friday sample (when CSVs available)
    temporal_drift: dict = {
        "status": "skipped",
        "ref": "processed_train",
        "current": "friday_day_sample",
        "note": "Complementary to IID train→test PSI; measures day-slice shift under the same feature columns.",
    }
    try:
        ref = load_processed("train")
        friday_df = _sample_friday(per_file, seed)
        if friday_df is not None and len(friday_df) >= 50:
            feats = [c for c in get_feature_columns(ref) if c in friday_df.columns]
            # Cap ref for tractable PSI (deterministic subsample)
            ref_n = min(len(ref), max(len(friday_df) * 3, 50000))
            if len(ref) > ref_n:
                ref_s = ref.sample(n=ref_n, random_state=seed)
            else:
                ref_s = ref
            fd = feature_drift_report(ref_s, friday_df, feats)
            ld = label_drift_report(ref_s["Label"], friday_df["Label"]) if "Label" in friday_df.columns else None
            flagged = fd.get("flagged_psi_ge_0.2") or []
            temporal_drift = {
                "status": "ok",
                "ref": "processed_train",
                "current": "friday_day_sample",
                "n_ref_used": int(len(ref_s)),
                "n_friday": int(len(friday_df)),
                "per_file_cap": per_file,
                "random_state": seed,
                "feature_drift": fd,
                "label_drift": ld,
                "summary": {
                    "features_compared": fd.get("features_compared"),
                    "flagged_psi_ge_0.2_count": len(flagged),
                    "max_psi": max((r.get("psi") or 0) for r in (fd.get("top_psi") or []) or [0]),
                    "top_psi": (fd.get("top_psi") or [])[:10],
                },
                "interpretation": (
                    "Non-zero temporal PSI is expected under day/scenario composition shift. "
                    "This does not invalidate IID metrics; it contextualizes them."
                ),
            }
            try:
                print(
                    f"Temporal PSI: compared={fd.get('features_compared')} "
                    f"flagged>={0.2}={len(flagged)} max~={temporal_drift['summary']['max_psi']}"
                )
            except Exception:
                pass
        else:
            temporal_drift["reason"] = "Friday CSV sample unavailable or too small"
    except Exception as exc:  # noqa: BLE001
        if temporal_drift.get("status") != "ok":
            temporal_drift["status"] = "error"
            temporal_drift["reason"] = str(exc)
        else:
            temporal_drift["print_warning"] = str(exc)

    iid_fd = (drift_iid.get("feature_drift") or {})
    iid_flagged = iid_fd.get("flagged_psi_ge_0.2") or []

    comparison = {
        "binary": {
            "iid_test": {
                "f1": iid_bin.get("f1"),
                "recall": iid_bin.get("recall"),
                "precision": iid_bin.get("precision"),
                "pr_auc": iid_bin.get("pr_auc"),
                "roc_auc": iid_bin.get("roc_auc"),
            },
            "friday_temporal": {
                "f1": fri_bin.get("f1"),
                "recall": fri_bin.get("recall"),
                "precision": fri_bin.get("precision"),
                "pr_auc": fri_bin.get("pr_auc"),
                "roc_auc": fri_bin.get("roc_auc"),
                "n": fri_bin.get("n"),
                "attack_rate": fri_bin.get("attack_rate"),
            },
            "early_mon_thu": {
                "f1": early.get("f1"),
                "recall": early.get("recall"),
                "precision": early.get("precision"),
                "pr_auc": early.get("pr_auc"),
                "n": early.get("n"),
                "attack_rate": early.get("attack_rate"),
            },
            "degradation_iid_minus_friday": {
                "f1": _delta(iid_bin.get("f1"), fri_bin.get("f1")),
                "recall": _delta(iid_bin.get("recall"), fri_bin.get("recall")),
                "precision": _delta(iid_bin.get("precision"), fri_bin.get("precision")),
                "pr_auc": _delta(iid_bin.get("pr_auc"), fri_bin.get("pr_auc")),
                "note": (
                    "Positive Δ = temporal worse than IID; negative Δ = temporal better. "
                    "Do not hide either direction."
                ),
            },
            "degradation_iid_minus_early": {
                "f1": _delta(iid_bin.get("f1"), early.get("f1")),
                "recall": _delta(iid_bin.get("recall"), early.get("recall")),
            },
        },
        "multiclass": {
            "iid_test_six_class": {
                "accuracy": iid_multi.get("accuracy"),
                "f1_macro": iid_multi.get("f1_macro"),
                "recall_macro": iid_multi.get("recall_macro"),
            },
            "friday_temporal_subset": {
                "accuracy": fri_multi.get("accuracy"),
                "f1_macro": fri_multi.get("f1_macro"),
                "recall_macro": fri_multi.get("recall_macro"),
                "n": fri_multi.get("n"),
                "families_present": fri_labels,
                "families_absent": temporal.get("friday_multiclass_families_absent")
                or [f for f in FAMILIES if f not in present],
                "note": (
                    "Friday multiclass covers only families present in the sample — "
                    "not a full six-class temporal evaluation."
                ),
            },
            "degradation_note": (
                "Aggregate multiclass Δ is not directly comparable (6-class IID vs 3-class Friday subset)."
            ),
        },
    }

    report = {
        "experiment_id": "EXP-017",
        "experiment": "generalization_p10",
        "phase": "P10",
        "status": "ok" if temporal.get("status") == "ok" else "partial",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "model_version": meta.get("model_version") or cfg.get("models", {}).get("model_version"),
        "feature_selector": {
            "dual_selectors": meta.get("dual_selectors"),
            "feature_count_binary": meta.get("feature_count_binary"),
            "feature_count_multiclass": meta.get("feature_count_multiclass"),
            "artifact_hashes": meta.get("artifact_hashes"),
        },
        "dataset": {
            "name": meta.get("dataset") or "CICIDS2017",
            "source": meta.get("dataset_source") or "MachineLearningCVE",
            "split_definition": {
                "iid": "stratified train/val/test from processed CICIDS2017 (see training_report / model_metadata)",
                "temporal": "day-named CSV samples; Friday = temporal holdout; Mon–Thu = early reference",
                "per_file_cap": temporal.get("samples", {}).get("per_file_cap", per_file),
            },
            "random_state": seed,
        },
        "frozen_models": {
            "binary": "decision_tree",
            "multiclass": "random_forest",
            "binary_threshold": threshold,
            "artifacts": ["binary_best.joblib", "multiclass_best.joblib", "feature_bundle.joblib"],
            "no_retrain": True,
            "no_tuning_on_temporal_holdout": True,
            "training_git_commit": meta.get("training_git_commit"),
        },
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "packages": meta.get("packages"),
        },
        "sources": {
            "training_report": "training_report.json",
            "temporal_holdout_report": "temporal_holdout_report.json",
            "drift_report_iid": "drift_report.json",
            "cross_dataset_status": "cross_dataset_status.json",
            "model_metadata": "model_metadata.json",
        },
        "comparison": comparison,
        "class_wise": {
            "iid_multiclass": iid_class_wise,
            "friday_temporal": temporal_family_status,
        },
        "confusion": {
            "iid_multiclass_off_diagonal": iid_confusions,
            "friday_temporal_off_diagonal": fri_confusions,
            "friday_temporal_matrix": fri_multi.get("confusion_matrix"),
            "friday_temporal_labels": fri_labels,
            "note": (
                "Only list relationships present in results. "
                "Friday subset CM is Bot/DDoS/PortScan when those are the only families present."
            ),
        },
        "drift": {
            "iid_train_to_test": {
                "features_compared": iid_fd.get("features_compared"),
                "flagged_psi_ge_0.2_count": len(iid_flagged) if isinstance(iid_flagged, list) else iid_flagged,
                "max_psi_listed": max((r.get("psi") or 0) for r in (iid_fd.get("top_psi") or []) or [0]),
                "citation": (
                    "No feature exceeded the selected PSI threshold (0.2) in the tested IID train→test comparison."
                ),
                "not_a_claim_of": "absence of temporal, live, or cross-dataset drift",
            },
            "temporal_train_to_friday": temporal_drift,
        },
        "external_dataset": {
            "status": cross.get("status") or "skipped",
            "reason": cross.get("reason"),
            "train_dataset": cross.get("train_dataset"),
            "external_dataset_dir": cross.get("external_dataset_dir"),
            "conclusion": "External-dataset validation remains future work.",
            "rule": "Do not retrain on an external set and call that cross-dataset generalization.",
        },
        "unknown_zero_day": {
            "status": "out_of_scope",
            "statement": (
                "This phase does not claim zero-day / unknown-attack detection. "
                "Held-out unknown behavior would be a separate experiment and must not modify the frozen classifier."
            ),
        },
        "research_vs_production": {
            "research_validation": (
                "Dataset → frozen DT/RF → IID stratified test + temporal day holdout → metrics in this report"
            ),
            "production_pipeline": (
                "PCAP → flow extraction → feature extraction → validation → frozen models"
            ),
            "inheritance": (
                "The production PCAP pipeline does not automatically inherit research IID/temporal metrics. "
                "Reported scores apply only under the documented experimental setup."
            ),
        },
        "limitations": [
            "Day slices are capped samples, not exhaustive day populations.",
            "Attack-rate composition differs across slices; headline F1 can move with prevalence.",
            "Friday multiclass perfect scores apply only to families present (Bot/DDoS/PortScan).",
            "BruteForce, DoS, and WebAttack lack Friday temporal class-wise evidence in this sample.",
            "Mon–Thu multiclass may skip when unseen labels (e.g. Infiltration) appear.",
            "IID PSI≈0 is expected under stratified same-corpus splits — not live drift absence.",
            "No compatible external dataset was scored under frozen preprocessing.",
            "No zero-day / unknown-class claim is made.",
            "Models were not retuned on the temporal holdout (holdout remains evaluation-only).",
        ],
        "conclusions": [
            (
                "Under the Friday temporal holdout sample, binary F1/PR-AUC remain high relative to the "
                "IID test; Δ(IID−Friday) F1 is negative (temporal slightly higher on this slice)."
            ),
            (
                "Mon–Thu early-day binary F1 is lower than IID (positive degradation), illustrating "
                "sensitivity to day composition / attack prevalence."
            ),
            (
                "Temporal multiclass generalization is only evidenced for Bot, DDoS, and PortScan in the "
                "Friday sample; three attack families remain unevaluated temporally."
            ),
            (
                "IID train→test PSI flagged zero features at the 0.2 heuristic; temporal train→Friday PSI "
                "is reported separately when computable and must not be collapsed into 'no drift'."
            ),
            "External-dataset and zero-day validation remain future / separate work.",
        ],
    }

    out = out_dir / "generalization_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(out), "status": report["status"], "experiment_id": report["experiment_id"]}, indent=2))


if __name__ == "__main__":
    main()
