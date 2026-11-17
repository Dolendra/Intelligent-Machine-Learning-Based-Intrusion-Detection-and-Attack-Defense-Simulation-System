"""R1a acceptance: every headline number in the papers traces to raw result artifacts.

* paper_numbers.json / paper_numbers.tex / generated tables must equal a fresh rebuild from the
  artifacts (so editing a result without regenerating, or editing the numbers by hand, fails);
* paper.tex may only use number macros that exist, and must \\input the generated files;
* claims removed by the R1 audit must not reappear in the paper sources or the guide.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs" / "research"
PAPER_TEX = RESEARCH / "paper.tex"
DOCX_BUILDER = RESEARCH / "paper_build" / "paper.py"
GUIDE = ROOT / "docs" / "AEGIS_GUIDE_PLAIN_LANGUAGE.md"


def _p59():
    spec = importlib.util.spec_from_file_location("p59", ROOT / "scripts" / "59_paper_numbers.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fresh():
    mod = _p59()
    return mod, mod.build()


def test_numbers_file_matches_artifacts(fresh):
    _, nums = fresh
    stored = json.loads((RESEARCH / "paper_numbers.json").read_text(encoding="utf-8"))
    assert set(stored) == set(nums), "number keys changed — rerun scripts/59_paper_numbers.py"
    stale = {k: (stored[k]["display"], nums[k]["display"]) for k in nums if stored[k]["display"] != nums[k]["display"]}
    assert not stale, f"paper_numbers.json is stale vs artifacts: {stale}"
    mod, _ = fresh
    assert (RESEARCH / "paper_numbers.tex").read_text(encoding="utf-8") == mod.render_tex(nums), \
        "paper_numbers.tex (incl. prose-fact macros) is stale — rerun scripts/59_paper_numbers.py"


def test_paper_tex_tables_are_canonical():
    """paper.tex must include tables only from research/publication.py output (no second generator)."""
    tex = PAPER_TEX.read_text(encoding="utf-8")
    inputs = re.findall(r"\\input\{([^}]*)\}", tex)
    assert all(i == "paper_numbers.tex" or i.startswith("publication/tables/") for i in inputs), inputs
    for i in inputs:
        assert (RESEARCH / i).exists(), f"missing generated file {i}"
    assert r"\begin{tabular}" not in tex, "hand-written tabular in paper.tex"


def test_paper_tex_uses_generated_numbers_only():
    tex = PAPER_TEX.read_text(encoding="utf-8")
    for inc in ("paper_numbers.tex", "publication/tables/loafo.tex", "publication/tables/significance.tex"):
        assert f"\\input{{{inc}}}" in tex, f"paper.tex must \\input {inc}"
    defined = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", (RESEARCH / "paper_numbers.tex").read_text(encoding="utf-8")))
    used = set(re.findall(r"\\([A-Z][A-Za-z]+)", tex)) - {"IEEEoverridecommandlockouts", "Delta"}  # LaTeX built-ins
    number_like = {u for u in used if u in defined or re.match(r"(Loafo|Temp|Cross|Delta|Tp|Pos|Frozen|Gate|Hth|Unseen|Range|Fam|Xai|Pool|Pair|Fact)", u)}
    undefined = number_like - defined
    assert not undefined, f"paper.tex uses undefined number macros: {sorted(undefined)}"
    # headline values must come from macros, not literals
    for literal in ("0.706", "0.490", "0.241", "7.09", "35.2"):
        assert literal not in tex, f"hard-coded headline number {literal} in paper.tex"


FORBIDDEN = {
    PAPER_TEX: ["7.68", "1.66\\%", "1.86 \\times", "provable", "Extreme Value Theory", "30 experimental runs",
                "ids-aegis.org", "across all models", "restores the false-alarm constraint"],
    DOCX_BUILDER: ["1.9×10^{−9}", "1.86×10^{−9}", "30 of 30 paired wins", "MITRE ATT&CK context for every detection",
                   "rather than the frozen detector's own test split"],
    GUIDE: ["1.9×10⁻⁹", "30 out of 30", "single hidden botnet flow", "locked out **27%**", "tags every detection with one"],
}


@pytest.mark.parametrize("path", list(FORBIDDEN), ids=lambda p: p.name)
def test_removed_claims_do_not_reappear(path):
    text = path.read_text(encoding="utf-8")
    hits = [s for s in FORBIDDEN[path] if s in text]
    assert not hits, f"{path.name} reintroduces audited claims: {hits}"


def test_guarantee_is_always_conditional():
    tex = PAPER_TEX.read_text(encoding="utf-8")
    abstract = tex.split("\\begin{abstract}")[1].split("\\end{abstract}")[0]
    assert "exchangeab" in abstract, "the abstract must state the exchangeability condition"
    assert "Conditional" in tex  # the theorem is titled as conditional
