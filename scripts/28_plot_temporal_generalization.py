"""Plot temporal-holdout generalization figures from temporal_holdout_report.json.

Does not require raw CICIDS CSVs — uses the frozen evaluation artifact only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import load_config, resolve_path

ATTACK_CLASSES = ["Bot", "BruteForce", "DDoS", "DoS", "PortScan", "WebAttack"]


def _round(x, n=5):
    return None if x is None else round(float(x), n)


def enrich_and_save(report: dict, path: Path) -> dict:
    """Add explicit class names, deltas, and honesty notes for report citation."""
    fri_m = (report.get("friday_temporal_holdout") or {}).get("multiclass") or {}
    present_idx = []
    class_wise = []
    if isinstance(fri_m.get("report"), dict):
        for k, v in fri_m["report"].items():
            if k.isdigit():
                idx = int(k)
                present_idx.append(idx)
                name = ATTACK_CLASSES[idx] if idx < len(ATTACK_CLASSES) else f"class_{idx}"
                class_wise.append(
                    {
                        "index": idx,
                        "attack_type": name,
                        "precision": v.get("precision"),
                        "recall": v.get("recall"),
                        "f1": v.get("f1-score"),
                        "support": v.get("support"),
                    }
                )
    iid_b = (report.get("iid_stratified_from_training_report") or {}).get("binary_test") or {}
    fri_b = (report.get("friday_temporal_holdout") or {}).get("binary") or {}
    early_b = (report.get("early_mon_thu") or {}).get("binary") or {}
    iid_m = (report.get("iid_stratified_from_training_report") or {}).get("multiclass_test") or {}

    def delta(a, b, key):
        if a.get(key) is None or b.get(key) is None:
            return None
        return _round(float(a[key]) - float(b[key]), 5)

    report["frozen_models"] = {
        "binary": "decision_tree",
        "multiclass": "random_forest",
        "binary_threshold": report.get("operating_threshold", 0.85),
        "artifacts": ["binary_best.joblib", "multiclass_best.joblib", "feature_bundle.joblib"],
        "no_retrain": True,
    }
    report["friday_multiclass_families_present"] = [
        ATTACK_CLASSES[i] for i in sorted(present_idx) if i < len(ATTACK_CLASSES)
    ]
    report["friday_multiclass_families_absent"] = [
        c for i, c in enumerate(ATTACK_CLASSES) if i not in set(present_idx)
    ]
    report["friday_multiclass_class_wise"] = class_wise
    report["comparison_tables"] = {
        "binary": {
            "iid_test": {
                "f1": iid_b.get("f1"),
                "precision": iid_b.get("precision"),
                "recall": iid_b.get("recall"),
                "roc_auc": iid_b.get("roc_auc"),
                "pr_auc": iid_b.get("pr_auc"),
                "fpr": iid_b.get("fpr"),
                "fnr": iid_b.get("fnr"),
            },
            "friday_temporal": {
                "f1": fri_b.get("f1"),
                "precision": fri_b.get("precision"),
                "recall": fri_b.get("recall"),
                "roc_auc": fri_b.get("roc_auc"),
                "pr_auc": fri_b.get("pr_auc"),
                "fpr": fri_b.get("fpr"),
                "fnr": fri_b.get("fnr"),
                "n": fri_b.get("n"),
                "attack_rate": fri_b.get("attack_rate"),
            },
            "early_mon_thu": {
                "f1": early_b.get("f1"),
                "precision": early_b.get("precision"),
                "recall": early_b.get("recall"),
                "roc_auc": early_b.get("roc_auc"),
                "n": early_b.get("n"),
                "attack_rate": early_b.get("attack_rate"),
            },
            "delta_iid_minus_friday": {
                "f1": delta(iid_b, fri_b, "f1"),
                "recall": delta(iid_b, fri_b, "recall"),
                "precision": delta(iid_b, fri_b, "precision"),
                "roc_auc": delta(iid_b, fri_b, "roc_auc"),
            },
            "delta_iid_minus_early": {
                "f1": delta(iid_b, early_b, "f1"),
                "recall": delta(iid_b, early_b, "recall"),
            },
        },
        "multiclass": {
            "iid_test_six_class": {
                "accuracy": iid_m.get("accuracy"),
                "f1_macro": iid_m.get("f1_macro"),
                "f1_weighted": iid_m.get("f1_weighted"),
            },
            "friday_temporal_subset": {
                "accuracy": fri_m.get("accuracy"),
                "f1_macro": fri_m.get("f1_macro"),
                "f1_weighted": fri_m.get("f1_weighted"),
                "n_attacks": fri_m.get("n"),
                "families_present": report["friday_multiclass_families_present"],
                "families_absent": report["friday_multiclass_families_absent"],
                "note": (
                    "Friday multiclass metrics cover only families present in the Friday sample "
                    "after attack-only encoding — not a full six-class temporal evaluation."
                ),
            },
        },
    }
    report["academic_caveats"] = [
        "Frozen Decision Tree / Random Forest joblibs were scored without retraining.",
        "Day slices are capped samples (per_file_cap), not exhaustive day populations.",
        "Attack-rate composition differs sharply across day slices; headline F1 can rise or fall with prevalence.",
        "Friday multiclass perfect scores apply only to Bot/DDoS/PortScan present in that sample.",
        "Mon–Thu multiclass scoring skipped when rare labels (e.g. Infiltration) appear outside the freeze class set.",
        "This is not evidence of live-network generalization or production IDS readiness.",
        "External-dataset validation was not performed within the current experimental scope and is identified as future work for assessing cross-dataset generalization.",
    ]
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def plot_binary_comparison(report: dict, out: Path) -> None:
    tbl = report["comparison_tables"]["binary"]
    metrics = ["f1", "precision", "recall", "roc_auc"]
    labels = ["F1", "Precision", "Recall", "ROC-AUC"]
    iid = [float(tbl["iid_test"][m]) for m in metrics]
    fri = [float(tbl["friday_temporal"][m]) for m in metrics]
    early = [float(tbl["early_mon_thu"][m]) for m in metrics]

    x = np.arange(len(metrics))
    w = 0.25
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    ax.bar(x - w, iid, w, label="IID stratified test", color="#1f4e79")
    ax.bar(x, fri, w, label="Friday temporal sample", color="#2a9d8f")
    ax.bar(x + w, early, w, label="Mon–Thu sample", color="#e9c46a")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.95, 1.005)
    ax.set_ylabel("Score")
    ax.set_title("Binary detection: IID vs temporal day samples (frozen Decision Tree @ 0.85)")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "temporal_binary_iid_vs_holdout.png", dpi=160)
    plt.close(fig)


def plot_multiclass_comparison(report: dict, out: Path) -> None:
    iid = report["comparison_tables"]["multiclass"]["iid_test_six_class"]
    fri = report["comparison_tables"]["multiclass"]["friday_temporal_subset"]
    metrics = ["accuracy", "f1_macro", "f1_weighted"]
    labels = ["Accuracy", "Macro-F1", "Weighted-F1"]
    iid_v = [float(iid[m]) for m in metrics]
    fri_v = [float(fri[m]) for m in metrics]

    x = np.arange(len(metrics))
    w = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x - w / 2, iid_v, w, label="IID test (6 attack classes)", color="#1f4e79")
    ax.bar(
        x + w / 2,
        fri_v,
        w,
        label="Friday sample (subset: " + ", ".join(fri["families_present"]) + ")",
        color="#2a9d8f",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.99, 1.002)
    ax.set_title("Multiclass: IID (6-class) vs Friday temporal subset (not full 6-class)")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "temporal_multiclass_iid_vs_holdout.png", dpi=160)
    plt.close(fig)


def plot_friday_cm(report: dict, out: Path) -> None:
    fri = (report.get("friday_temporal_holdout") or {}).get("multiclass") or {}
    cm = np.array(fri.get("confusion_matrix") or [], dtype=float)
    names = report.get("friday_multiclass_families_present") or []
    if cm.size == 0 or not names:
        return
    fig, ax = plt.subplots(figsize=(5.5, 4.8))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(names)))
    ax.set_yticks(range(len(names)))
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_yticklabels(names)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Friday temporal multiclass CM (families present only)")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", color="black", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(out / "temporal_friday_multiclass_confusion.png", dpi=160)
    plt.close(fig)


def plot_classwise_support(report: dict, out: Path) -> None:
    rows = report.get("friday_multiclass_class_wise") or []
    if not rows:
        return
    names = [r["attack_type"] for r in rows]
    supports = [float(r["support"]) for r in rows]
    f1s = [float(r["f1"]) for r in rows]
    fig, ax1 = plt.subplots(figsize=(7, 4.2))
    x = np.arange(len(names))
    ax1.bar(x, supports, color="#457b9d", label="Support (n)")
    ax1.set_ylabel("Support")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names)
    ax2 = ax1.twinx()
    ax2.plot(x, f1s, "o-", color="#e76f51", label="F1")
    ax2.set_ylabel("F1")
    ax2.set_ylim(0.9, 1.05)
    ax1.set_title("Friday temporal: class-wise support vs F1 (present families)")
    fig.tight_layout()
    fig.savefig(out / "temporal_friday_classwise.png", dpi=160)
    plt.close(fig)


def plot_summary_card(report: dict, out: Path) -> None:
    b = report["comparison_tables"]["binary"]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.axis("off")
    lines = [
        "Temporal generalization summary (frozen v1.1)",
        "",
        f"Binary model: Decision Tree @ {report.get('operating_threshold', 0.85)}",
        f"Multiclass model: Random Forest (attack-only)",
        "",
        f"IID binary F1:     {b['iid_test']['f1']:.5f}",
        f"Friday binary F1:  {b['friday_temporal']['f1']:.5f}  (n={b['friday_temporal']['n']}, attack_rate={b['friday_temporal']['attack_rate']:.3f})",
        f"Mon–Thu binary F1: {b['early_mon_thu']['f1']:.5f}  (n={b['early_mon_thu']['n']}, attack_rate={b['early_mon_thu']['attack_rate']:.3f})",
        f"Δ F1 (IID − Friday): {b['delta_iid_minus_friday']['f1']:+.5f}",
        f"Δ F1 (IID − Mon–Thu): {b['delta_iid_minus_early']['f1']:+.5f}",
        "",
        "Friday multiclass families present: " + ", ".join(report.get("friday_multiclass_families_present") or []),
        "Friday multiclass families absent:  " + ", ".join(report.get("friday_multiclass_families_absent") or []),
        "",
        "Not a live-network claim. External-dataset validation = future work.",
    ]
    ax.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "temporal_generalization_summary.png", dpi=160)
    plt.close(fig)


def main() -> None:
    cfg = load_config()
    model_dir = resolve_path(cfg["models"]["output_dir"])
    report_path = model_dir / "temporal_holdout_report.json"
    if not report_path.exists():
        raise SystemExit(f"Missing {report_path}; run scripts/25_temporal_holdout_eval.py first.")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report = enrich_and_save(report, report_path)

    out = model_dir / "figures"
    out.mkdir(parents=True, exist_ok=True)
    plot_binary_comparison(report, out)
    plot_multiclass_comparison(report, out)
    plot_friday_cm(report, out)
    plot_classwise_support(report, out)
    plot_summary_card(report, out)

    print(
        json.dumps(
            {
                "enriched": str(report_path),
                "figures": [
                    "temporal_binary_iid_vs_holdout.png",
                    "temporal_multiclass_iid_vs_holdout.png",
                    "temporal_friday_multiclass_confusion.png",
                    "temporal_friday_classwise.png",
                    "temporal_generalization_summary.png",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
