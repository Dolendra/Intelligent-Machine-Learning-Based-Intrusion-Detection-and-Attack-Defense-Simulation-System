"""Export a markdown comparison table from training_report.json for the project report."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ids_config import resolve_path, load_config


def main() -> None:
    cfg = load_config()
    path = resolve_path(cfg["models"]["output_dir"]) / "training_report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    bval = report["binary"]["validation"]
    mval = report["multiclass"]["validation"]
    lines = [
        "# Model comparison (from training_report.json)",
        "",
        f"**Frozen selection (v1.1):** binary = `{report['binary']['best']}` · multiclass = `{report['multiclass']['best']}`",
        "Binary selection is **multi-objective** (recall / F1 / PR-AUC / FPR / latency).",
        "",
        "## Binary validation",
        "",
        "| Model | Precision | Recall | F1 | ROC-AUC | selection_score |",
        "|-------|----------:|-------:|---:|--------:|----------------:|",
    ]
    for name, m in bval.items():
        star = "**" if name == report["binary"]["best"] else ""
        lines.append(
            f"| {star}{name}{star} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | "
            f"{m.get('roc_auc', 0):.4f} | {m.get('selection_score', 0):.6f} |"
        )
    bt = report["binary"]["test"]
    lines += [
        "",
        f"**Best binary:** `{report['binary']['best']}`",
        f"**Test:** precision={bt['precision']:.5f}, recall={bt['recall']:.5f}, F1={bt['f1']:.5f}, "
        f"ROC-AUC={bt.get('roc_auc')}",
        "",
        "## Multiclass validation (attack-only)",
        "",
        "| Model | macro-F1 | weighted-F1 | accuracy | selection_score |",
        "|-------|---------:|------------:|---------:|----------------:|",
    ]
    for name, m in mval.items():
        star = "**" if name == report["multiclass"]["best"] else ""
        lines.append(
            f"| {star}{name}{star} | {m['f1_macro']:.4f} | {m['f1_weighted']:.4f} | "
            f"{m['accuracy']:.4f} | {m.get('selection_score', 0):.6f} |"
        )
    mt = report["multiclass"]["test"]
    lines += [
        "",
        f"**Best multiclass:** `{report['multiclass']['best']}`",
        f"**Test:** macro-F1={mt['f1_macro']:.5f}, weighted-F1={mt['f1_weighted']:.5f}",
        "",
    ]
    out = resolve_path(cfg["models"]["output_dir"]) / "model_comparison.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
