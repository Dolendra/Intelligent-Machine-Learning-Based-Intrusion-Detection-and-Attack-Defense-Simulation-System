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
    lines = [
        "# Model comparison (from training_report.json)",
        "",
        "## Binary validation",
        "",
        "| Model | Precision | Recall | F1 | ROC-AUC |",
        "|-------|----------:|-------:|---:|--------:|",
    ]
    for name, m in report["binary"]["validation"].items():
        roc = m.get("roc_auc")
        roc_s = f"{roc:.4f}" if isinstance(roc, (int, float)) else "—"
        lines.append(
            f"| {name} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {roc_s} |"
        )
    bt = report["binary"]["test"]
    lines += [
        "",
        f"**Best binary:** `{report['binary']['best']}`",
        f"**Test:** precision={bt['precision']:.4f}, recall={bt['recall']:.4f}, F1={bt['f1']:.4f}, ROC-AUC={bt.get('roc_auc')}",
        "",
        "## Multiclass validation (macro / weighted F1)",
        "",
        "| Model | macro-F1 | weighted-F1 | accuracy |",
        "|-------|---------:|------------:|---------:|",
    ]
    for name, m in report["multiclass"]["validation"].items():
        lines.append(
            f"| {name} | {m['f1_macro']:.4f} | {m['f1_weighted']:.4f} | {m['accuracy']:.4f} |"
        )
    mt = report["multiclass"]["test"]
    lines += [
        "",
        f"**Best multiclass:** `{report['multiclass']['best']}`",
        f"**Test:** macro-F1={mt['f1_macro']:.4f}, weighted-F1={mt['f1_weighted']:.4f}",
        "",
    ]
    out = resolve_path(cfg["models"]["output_dir"]) / "model_comparison.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
