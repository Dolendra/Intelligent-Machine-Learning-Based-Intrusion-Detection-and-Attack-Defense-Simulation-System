"""R1b acceptance: every publication number and table traces to committed result artifacts.

1. Generated tables/facts (JSON, Markdown, LaTeX) equal a fresh rebuild from the artifacts.
2. The built DOCX contains exactly the canonical tables, cell for cell, in the declared order.
3. The DOCX builder has no hand-typed tables and no result-like literal numbers in its prose.
4. Paper figures that show data are byte-identical to the figures regenerated from artifacts.
5. Every artifact a table cites is committed (not git-ignored).
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBDIR = ROOT / "docs" / "research" / "publication"
BUILDER = ROOT / "docs" / "research" / "paper_build" / "paper.py"
FIGDIR = ROOT / "docs" / "research" / "paper_build" / "figs"
DOCX = ROOT / "docs" / "research" / "Aegis_Research_Paper.docx"


@pytest.fixture(scope="module")
def fresh():
    from research import publication as pub

    return pub, pub.build_tables(), pub.facts()


def test_generated_files_match_artifacts(fresh):
    pub, tables, fx = fresh
    assert (PUBDIR / "publication_tables.json").read_text(encoding="utf-8") == pub.render_json(tables, fx), \
        "publication_tables.json is stale — run scripts/62_publication_tables.py"
    assert (PUBDIR / "TABLES.md").read_text(encoding="utf-8") == pub.render_markdown(tables)
    for key, t in tables.items():
        assert (PUBDIR / "tables" / f"{key}.tex").read_text(encoding="utf-8") == pub.to_latex(t), key


def _builder_order() -> list[str]:
    src = BUILDER.read_text(encoding="utf-8")
    order = ast.literal_eval(re.search(r"TABLE_ORDER = (\[.*?\])", src, re.S).group(1))
    calls = re.findall(r'^PT\("([a-z0-9_]+)"', src, re.M)
    return order, calls


def test_builder_uses_canonical_tables_only():
    src = BUILDER.read_text(encoding="utf-8")
    order, calls = _builder_order()
    assert calls == order, "PT() calls must follow TABLE_ORDER (table numbering depends on it)"
    direct = [n.lineno for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call)
              and getattr(n.func, "attr", "") == "table" and getattr(n.func.value, "id", "") == "P"]
    assert len(direct) == 1, f"P.table may only be called inside PT(); found at lines {direct}"


def test_builder_prose_has_no_result_literals():
    from research.literal_scan import violations

    v = violations(BUILDER)
    assert not v, "hand-typed result numbers in the paper builder: " + "; ".join(f"L{l} {t}" for l, t, _ in v)


def _docx_tables() -> list[list[list[str]]]:
    doc = zipfile.ZipFile(DOCX).read("word/document.xml").decode("utf-8")
    out = []
    for tbl in re.findall(r"<w:tbl>.*?</w:tbl>", doc, re.S):
        rows = []
        for tr in re.findall(r"<w:tr[ >].*?</w:tr>", tbl, re.S):
            rows.append(["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tc)).strip()
                         for tc in re.findall(r"<w:tc>.*?</w:tc>", tr, re.S)])
        # the builder lays out numbered equations as one-row tables: ['', '(3)'] — not data tables
        if len(rows) == 1 and re.fullmatch(r"\(\d+\)", rows[0][-1] or ""):
            continue
        out.append(rows)
    return out


def _subscript_symbols() -> list[str]:
    """The symbols docbuilder renders with a subscript (its _SUBS list), read from its source."""
    src = (ROOT / "docs" / "research" / "paper_build" / "docbuilder.py").read_text(encoding="utf-8")
    return list(ast.literal_eval(re.search(r"for k in (\(.*?\))\]", src, re.S).group(1)))


_SUBSCRIPTED = _subscript_symbols()


def _plain(cell: str) -> str:
    """Text as the DOCX shows it: markup removed, subscripted symbols joined (AUROC_u → AUROCu)."""
    s = cell.replace("**", "").strip()
    for sym in _SUBSCRIPTED:
        s = s.replace(sym, sym.replace("_", ""))
    s = re.sub(r"\^\{([^}]*)\}", r"\1", s)  # superscript markup → rendered text
    return re.sub(r"\s+", " ", s)


@pytest.mark.skipif(not DOCX.exists(), reason="paper not built")
def test_docx_tables_equal_canonical_tables(fresh):
    _, tables, _ = fresh
    order, _ = _builder_order()
    built = _docx_tables()
    assert len(built) == len(order), f"DOCX has {len(built)} tables, expected {len(order)}"
    for key, got in zip(order, built):
        t = tables[key]
        want = [[_plain(h) for h in t.header]] + [[_plain(c) for c in r] for r in t.rows]
        got = [[re.sub(r"\s+", " ", c) for c in r] for r in got]
        assert got == want, f"DOCX table '{key}' differs from the canonical table — rebuild the paper"


def test_data_figures_are_regenerated_copies():
    src = (ROOT / "docs" / "research" / "paper_build" / "make_figs.py").read_text(encoding="utf-8")
    mapping = ast.literal_eval(re.search(r"GENERATED = (\{.*?\})", src, re.S).group(1))
    for dst, s in mapping.items():
        a = hashlib.sha256((FIGDIR / dst).read_bytes()).hexdigest()
        b = hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
        assert a == b, f"{dst} is not the current {s} — run make_figs.py"


def test_cited_sources_are_committed(fresh):
    _, tables, fx = fresh
    files = {s.split(":")[0] for t in tables.values() for s in t.sources}
    files |= {f.source.split(":")[0] for f in fx.values() if ":" in f.source and "/" in f.source.split(":")[0]}
    ignored = []
    for f in sorted(files):
        assert (ROOT / f).exists(), f"cited source missing: {f}"
        if subprocess.run(["git", "check-ignore", "-q", f], cwd=ROOT).returncode == 0:
            ignored.append(f)
    assert not ignored, f"cited sources are git-ignored (not committed evidence): {ignored}"


def test_every_fact_has_a_source(fresh):
    _, _, fx = fresh
    assert all(f.source for f in fx.values())
    assert all(f.display not in ("", "None", "nan", "nan%") for f in fx.values()), \
        [k for k, f in fx.items() if f.display in ("", "None", "nan", "nan%")]
