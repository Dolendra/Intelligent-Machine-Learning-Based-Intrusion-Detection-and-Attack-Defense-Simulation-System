"""Validate the compiled LaTeX paper against the canonical publication data (R1b).

    python scripts/63_validate_latex_pdf.py --pdf <compiled paper.pdf> [--log <paper.log>]

Checks (all must pass):
  1. every numeric token of every table that paper.tex \\inputs appears in the PDF text;
  2. every number macro used in paper.tex appears (its rendered value) in the PDF text;
  3. no unresolved-reference markers ("??") and no placeholder text (TODO, TBD, XXX, lorem);
  4. headline facts shared with the DOCX paper appear in BOTH PDFs (LaTeX and the DOCX export);
  5. if a LaTeX log is given: no undefined references/citations and no overfull boxes.
It also records the SHA-256 of every LaTeX input, so tests can detect a source edited after validation.

Writes docs/research/publication/latex_validation.json and copies the PDF to
docs/research/Aegis_OSR_paper_ieee.pdf.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from pypdf import PdfReader  # noqa: E402

from research import publication as pub  # noqa: E402

RESEARCH = ROOT / "docs" / "research"
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
HEADLINE = ["osr_zdr", "xgb_zdr", "dt_zdr", "osr_fpr", "x_frozen_f1", "x_osr_fpr", "pd_recal2000_fpr",
            "pd_recal2000_known", "pd_recal2000_zdr", "t_fri_osr_fpr"]


def pdf_text(path: Path) -> str:
    text = " ".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    text = text.replace("\u2212", "-").replace("\ufb01", "fi").replace("\ufb02", "fl")
    return re.sub(r"\s+", " ", text)


def input_hashes(included: list[str]) -> dict[str, str]:
    """SHA-256 of every LaTeX source the PDF was built from, so a stale validation is detectable."""
    paths = [RESEARCH / "paper.tex", RESEARCH / "paper_numbers.tex"]
    paths += [RESEARCH / "publication" / "tables" / f"{k}.tex" for k in included]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def tokens(s: str) -> list[str]:
    return [t.replace(",", "") for t in NUM.findall(s)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--log")
    a = ap.parse_args()
    pdf = Path(a.pdf)
    text = pdf_text(pdf)
    pdf_tokens = set(tokens(text))
    tex = (RESEARCH / "paper.tex").read_text(encoding="utf-8")
    report: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "pdf_sha256":
                    hashlib.sha256(pdf.read_bytes()).hexdigest(), "pages": len(PdfReader(str(pdf)).pages), "checks": {}}

    tables = pub.build_tables()
    included = [Path(i).stem for i in re.findall(r"\\input\{publication/tables/([^}]*)\}", tex)]
    missing_tab = {}
    for key in included:
        t = tables[key]
        cells = [c for r in t.rows for c in r] + list(t.header)
        need = {tok for c in cells for tok in tokens(c.replace("**", ""))}
        miss = sorted(need - pdf_tokens)
        if miss:
            missing_tab[key] = miss
    report["checks"]["tables"] = {"included": included, "missing_numeric_tokens": missing_tab, "pass": not missing_tab}
    report["inputs_sha256"] = input_hashes(included)

    macros = {}
    for line in (RESEARCH / "paper_numbers.tex").read_text(encoding="utf-8").splitlines():
        mm = re.match(r"\\newcommand\{\\([A-Za-z]+)\}\{(.*)\}$", line)
        if mm:
            macros[mm.group(1)] = mm.group(2)
    used = sorted(set(re.findall(r"\\([A-Z][A-Za-z]+)", tex)) & set(macros))
    miss_mac = {m_: macros[m_] for m_ in used if not set(tokens(macros[m_])) <= pdf_tokens}
    report["checks"]["macros"] = {"used": len(used), "missing": miss_mac, "pass": not miss_mac}

    markers = [w for w in ("??", "TODO", "TBD", "XXX", "lorem", "[?]") if w.lower() in text.lower()]
    report["checks"]["placeholders"] = {"found": markers, "pass": not markers}

    fx = pub.facts()
    docx_pdf = RESEARCH / "Aegis_Research_Paper.pdf"
    docx_text = pdf_text(docx_pdf) if docx_pdf.exists() else ""
    docx_tokens = set(tokens(docx_text))
    head = {}

    def renderings(f) -> list[set[str]]:
        """The same value as the papers may print it: as displayed, or as proportion / percentage."""
        forms = [set(tokens(f.display))]
        v = f.value
        if isinstance(v, (int, float)) and 0 <= v <= 1:
            forms += [{f"{v:.3f}"}, {f"{100 * v:.1f}"}, {f"{100 * v:.2f}"}]
        return forms

    for k in HEADLINE:
        forms = renderings(fx[k])
        head[k] = {"value": fx[k].display,
                   "in_latex_pdf": any(fm <= pdf_tokens for fm in forms),
                   "in_docx_pdf": any(fm <= docx_tokens for fm in forms)}
    report["checks"]["headline_cross_document"] = {"facts": head, "pass": all(v["in_latex_pdf"] and v["in_docx_pdf"]
                                                                             for v in head.values())}
    if a.log:
        log = Path(a.log).read_text(encoding="utf-8", errors="replace")
        und = re.findall(r"(?:Reference|Citation) `[^']+' on page \d+ undefined", log)
        over = re.findall(r"Overfull \\hbox", log)
        report["checks"]["latex_log"] = {"undefined": und, "overfull_boxes": len(over),
                                         "pass": not und and not over}
    report["pass"] = all(c["pass"] for c in report["checks"].values())
    out = RESEARCH / "publication" / "latex_validation.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    shutil.copyfile(pdf, RESEARCH / "Aegis_OSR_paper_ieee.pdf")
    print(json.dumps({k: v["pass"] for k, v in report["checks"].items()}, indent=1), "\nOVERALL:", report["pass"])
    if not report["pass"]:
        print(json.dumps(report["checks"], indent=1, ensure_ascii=False)[:3000])
        sys.exit(1)


if __name__ == "__main__":
    main()
