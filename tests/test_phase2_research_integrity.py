"""Phase 2 (research integrity): corrected claims stay corrected, and corrected numbers trace to versioned artifacts.

Findings covered (docs/research/ML_PIPELINE_AUDIT.md): ML-1, ML-2, ML-3, ML-4, ML-10, ML-12, RES-1, RES-3, RES-4, RES-11.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RA = ROOT / "research_artifacts"
REEVAL = RA / "v11_reeval"
REANALYSIS = RA / "reanalysis"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ----------------------------------------------------------------------------- forbidden / required phrases
# Phrases that state a corrected claim as fact. A document may keep the historical wording only inside a quoted,
# clearly marked correction, so each check looks at text outside lines that start with ">" (block quotes).
FORBIDDEN = {
    "README.md": ["guaranteed benign false-alarm rate", "restores false-alarm control"],
    "docs/research/AEGIS_OSR.md": ["restores exchangeability"],
    "docs/research/paper.tex": ["Evidence points to a confound", "a classifier retrained on CICIDS2017",
                                "cannot create separation the evidence lacks", "partly restores the budget"],
    "docs/research/paper_build/paper.py": ["a classifier retrained on CICIDS2017",
                                           "cannot create separation that the evidence does not contain",
                                           "largely restored it without retraining",
                                           "the controlled test plane measured the response chain directly"],
    "docs/research/PRIOR_WORK_COMPARISON.md": ["so the inversion is specific to the cross-network setting"],
    "docs/PROJECT_REPORT.md": ["### Binary test results (Decision Tree @ 0.85)", "ports where configured",
                               "| **Controlled-lab (P11)** | Measured outcomes"],
    "docs/VIVA_QA.md": ["### Binary test (DT @ 0.85) — research", "| Friday binary F1 | **0.99770** |",
                        "P11 measured **1.00/0.80**", "ports (as configured)"],
    "docs/PRESENTATION.md": ["## Slide 14 — P11 empirical mitigation"],
    "docs/DEMO.md": ["Research IID binary F1 is **0.99048**", "we separately measured mitigation in P11"],
    "frontend/src/pages/ModelsPage.tsx": ['subtitle="Binary detector at the operating threshold"'],
}


def _unquoted(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))


@pytest.mark.parametrize("rel,phrases", sorted(FORBIDDEN.items()))
def test_corrected_claims_do_not_reappear(rel, phrases):
    body = _unquoted(_read(rel))
    found = [p for p in phrases if p in body]
    assert not found, f"{rel} restates a corrected claim: {found}"


@pytest.mark.parametrize("rel", ["docs/GENERALIZATION.md", "docs/PROJECT_REPORT.md", "docs/VIVA_QA.md"])
def test_p10_temporal_result_is_marked_superseded(rel):
    """ML-3: the script-25 Friday result scored training rows; every document quoting it must say so."""
    text = _read(rel)
    assert "0.99770" not in text or re.search(r"(?i)superseded", text), rel
    assert re.search(r"(?i)contaminated", text), rel


def test_readme_states_conditional_guarantee_and_policy_rates():
    text = _read("README.md")
    assert "exchangeable" in text
    assert "0.077 %" in text and "0.934 %" in text  # E-03 benign incident rate per policy


# ----------------------------------------------------------------------------- versioned artifacts (E-01..E-05)
def _json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_e01_reproduces_historical_figure_at_argmax_not_at_deployed_threshold():
    e = _json(REEVAL / "v11_test_metrics_by_threshold.json")
    a = e["reproduction_anchor"]
    assert a["reproduced_at_0.5"] is True
    assert max(a["abs_diff_vs_recomputed_at_0.5"].values()) <= 1e-9
    assert max(a["abs_diff_vs_recomputed_at_0.85"].values()) > 1e-3  # ML-1: the "@0.85" label was wrong
    assert e["test_data_used_for_selection"] is False
    meta = _json(ROOT / "models" / "trained_models" / "model_metadata.json")
    assert meta["binary_threshold"] == 0.85
    assert e["metrics"]["0.85"]["fpr"] < e["metrics"]["0.5"]["fpr"]


def test_e02_minority_families_reported_end_to_end():
    e = _json(REEVAL / "v11_family_end_to_end.json")
    pf = e["per_family"]
    for fam in ("Bot", "WebAttack", "BruteForce", "DDoS", "DoS", "PortScan"):
        r = pf[fam]
        assert r["end_to_end_correct@0.85"]["k"] <= r["detected@0.85"]["k"] <= r["n"]
    # the documented weakness: below 60 % at the deployed threshold
    assert pf["Bot"]["detected@0.85"]["rate"] < 0.6 and pf["WebAttack"]["detected@0.85"]["rate"] < 0.6
    assert e["end_to_end_system"]["0.85"]["macro_f1_7class"] < e["macro_f1_stage2_conditional_on_oracle_stage1"]


def test_e03_policy_rates_on_doubly_held_out_rows():
    e = _json(REEVAL / "v11_policy_alert_rates.json")
    assert all(v == 0 for v in e["overlap_check"].values())
    b = e["per_family"]["BENIGN"]
    assert b["frozen"]["rate"] <= b["union"]["rate"] and b["gate"]["rate"] <= b["union"]["rate"]
    assert b["n"] > 8000  # the full eligible set, not only the replay sample


def test_e04_reanalysis_reproduces_committed_records():
    s = _json(REANALYSIS / "matched_fpr_summary.json")
    assert s["reproduction_anchor"]["reproduced"] is True
    assert s["reproduction_anchor"]["values_checked"] > 1000
    assert "oracle" in s["status"]


@pytest.mark.parametrize("folder", [REEVAL, REANALYSIS])
def test_manifest_hashes_match_outputs(folder):
    import hashlib
    man = _json(folder / "MANIFEST.json")
    for rel, digest in man["outputs"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel


@pytest.mark.parametrize("script", ["71_v11_reeval.py", "72_matched_fpr_reanalysis.py"])
def test_reeval_scripts_refuse_to_overwrite(script):
    src = _read(f"scripts/{script}")
    assert "refusing to overwrite" in src and "assert_writable" in src


def test_inversion_table_covers_every_day_with_known_attacks():
    """RES-3: the per-day comparison is built from all days, not from a hand-picked subset."""
    import sys
    sys.path.insert(0, str(ROOT))
    from research import publication as pub
    t = pub.build_tables()["inversion"]
    s = _json(REANALYSIS / "matched_fpr_summary.json")["cross_perday"]["recal@2000"]["per_day_mean_over_seeds"]
    days = sorted(d for d, v in s.items() if v["Closed-set XGB"]["conformal_known_recall"] is not None)
    assert [r[0] for r in t.rows] == days and len(days) == 8
