"""Find result-like numbers typed as literals in publication sources (R1b).

A number is "result-like" if it is a decimal (0.706, 7.09), a percentage with a decimal (7.09%), or a
thousands-separated count (2,520,798). Design and configuration constants that legitimately appear
in prose (thresholds, caps, model hyper-parameters, software versions, weights) are allow-listed
explicitly below, each with a reason. Interpolated f-string expressions are not literals and are
ignored — they are read from artifacts at build time.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

RESULT_LIKE = re.compile(r"(?<![\w.^{])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)+%?)(?![\w}])")

# token -> reason. Everything here is a *design or configuration* value, not a measured result.
ALLOWED = {
    "0.85": "frozen operating threshold τ (config)", "0.95": "threshold-selection recall floor / band (config)",
    "0.10": "uncertainty band lower edge (config)", "0.99": "generic 'F1 above 0.99' literature statement",
    "0.98": "classification cut used in a sentence ('scored above 0.98')", "0.7": "multiclass selection weight (config)",
    "0.3": "multiclass selection weight (config)", "0.1": "XGBoost learning rate (hyper-parameter)",
    "0.8": "XGBoost subsampling (hyper-parameter)", "0.5": "attribution rule s_sup < 0.5 (design)",
    "0.25": "range stage rate multiplier / risk weight (config)", "0.4": "range stage rate multiplier (config)",
    "0.50": "risk weight (config)", "0.15": "risk weight (config)", "0.01": "α / α_fam (design)",
    "0.05": "α in a sentence (design)", "0.0625": "minimum two-sided Wilcoxon p for 5 seeds (mathematical fact)",
    "0.90": "robustness cut used for bolding (design)", "1.5": "range per-flow service cost / 1.5% band (config)",
    "1.5%": "per-day calibration tolerance used in a sentence (design)",
    "0.5×": "intensity setting", "3.11.9": "Python version", "1.9.0": "scikit-learn version", "3.2.0": "XGBoost version",
    "0.51.0": "SHAP version", "300,000": "training cap (config)", "60,000": "training/validation cap (config)",
    "10,000": "validation cap (config)", "150,000": "test cap / threshold rows (config)", "25,000": "test cap (config)",
    "40,000": "k-NN reference size (config)", "20,000": "deployed k-NN reference / per-label cap (config)",
    "30,000": "calibration split size (config)", "5,000": "warm-up window (design)", "2,000": "warm-up window (design)",
    "1,000": "example n in a formula / batch size (design)", "100,000": "2018 per-day attack cap (design)",
    "1.1": "frozen model version name (v1.1)", "0.30": "selection-score weight in the S equation (config)",
    "0.20": "selection-score weight in the S equation (config)", "0.2%": "misattribution cut used in a sentence (design)",
    "0.1%": "α setting in a sentence (design)",
    "10.1109": "DOI registrant prefix in a reference (IEEE)", "10.1007": "DOI registrant prefix in a reference (Springer)",
    "10.3390": "DOI registrant prefix in a reference (MDPI)", "10.3389": "DOI registrant prefix in a reference (Frontiers)",
}


def literals(path: Path) -> list[tuple[int, str, str]]:
    """(line, token, context) for result-like numbers in plain string constants (not f-string fields)."""
    src = path.read_text(encoding="utf-8")
    hits = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for mm in RESULT_LIKE.finditer(node.value):
                hits.append((node.lineno, mm.group(1), node.value[max(0, mm.start() - 40): mm.end() + 30]))
    # strings inside f-strings are Constant children of JoinedStr, so they are covered above
    return hits


def violations(path: Path, skip_lines: set[int] | None = None) -> list[tuple[int, str, str]]:
    return [h for h in literals(path) if h[1] not in ALLOWED and (not skip_lines or h[0] not in skip_lines)]
