"""Convert docs/PROJECT_REPORT.md into a Word document for submission."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def clean_inline(text: str) -> str:
    """Strip inline Markdown (links, code, bold, italic) so it does not appear as raw characters in Word."""
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<![\w*])\*([^*\s][^*]*?)\*(?![\w*])", r"\1", text)
    return text.strip()


def add_md_line(doc: Document, line: str) -> None:
    raw = line.rstrip()
    if not raw:
        return
    if raw.startswith("# "):
        doc.add_heading(clean_inline(raw[2:]), level=0)
        return
    if raw.startswith("## "):
        doc.add_heading(clean_inline(raw[3:]), level=1)
        return
    if raw.startswith("### "):
        doc.add_heading(clean_inline(raw[4:]), level=2)
        return
    if raw.startswith("---"):
        return
    if raw.startswith("|") and "---" not in raw:
        # Collect tables elsewhere; skip single rows here
        return
    if raw.startswith("```"):
        return
    if raw.startswith(">"):
        inner = raw.lstrip("> ")
        quoted_bullet = re.match(r"^[-*]\s+(.*)$", inner)
        p = doc.add_paragraph(clean_inline(quoted_bullet.group(1) if quoted_bullet else inner),
                              style="List Bullet" if quoted_bullet else None)
        for run in p.runs:
            run.italic = True
        return
    bullet = re.match(r"^(\s*)[-*]\s+(.*)$", raw)
    if bullet:
        style = "List Bullet 2" if len(bullet.group(1)) >= 2 else "List Bullet"
        doc.add_paragraph(clean_inline(bullet.group(2)), style=style)
        return
    if re.match(r"^\d+\.\s", raw):
        doc.add_paragraph(clean_inline(re.sub(r"^\d+\.\s+", "", raw)), style="List Number")
        return
    doc.add_paragraph(clean_inline(raw))


def add_table_from_rows(doc: Document, rows: list[list[str]]) -> None:
    if len(rows) < 2:
        return
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            table.rows[i].cells[j].text = clean_inline(cell)


BLOCK_START = re.compile(r"^\s*(#|\||```|[-*]\s|\d+\.\s|>|---)")


def join_wrapped(lines: list[str]) -> list[str]:
    """Join hard-wrapped Markdown lines into one paragraph so Word does not break sentences.

    A line is a continuation when it is not blank, does not start a new block, and the previous line is text that does
    not end in a Markdown hard break (two trailing spaces). Quote continuations (``> text``) join the previous quote
    line. Code blocks and tables are left untouched."""
    out: list[str] = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        prev = out[-1] if out else ""
        joinable_prev = (not in_code and prev.strip() and not prev.endswith("  ")
                         and not prev.strip().startswith(("|", "#", "```", "---")))
        if joinable_prev and line.strip():
            if line.startswith(">") and prev.startswith(">"):
                inner = line.lstrip("> ")
                if not re.match(r"^[-*]\s", inner):
                    out[-1] = prev.rstrip() + " " + inner.strip()
                    continue
            elif not BLOCK_START.match(line):
                out[-1] = prev.rstrip() + " " + line.strip()
                continue
        out.append(line)
    return out


def parse_markdown(md: str, doc: Document) -> None:
    lines = join_wrapped(md.splitlines())
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in row):
                    rows.append(row)
                i += 1
            add_table_from_rows(doc, rows)
            continue
        if line.strip().startswith("```"):
            i += 1
            block: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            p = doc.add_paragraph("\n".join(block))
            for run in p.runs:
                run.font.name = "Consolas"
                run.font.size = Pt(9)
            i += 1
            continue
        add_md_line(doc, line)
        i += 1


def main() -> None:
    md_path = ROOT / "docs" / "PROJECT_REPORT.md"
    out_path = ROOT / "docs" / "Aegis_IDS_Project_Report.docx"
    figures = ROOT / "models" / "trained_models" / "figures"

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    title = doc.add_heading("Aegis IDS", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph(
        "Intelligent Machine Learning–Based Intrusion Detection "
        "and Attack–Defense Simulation System"
    )
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

    parse_markdown(md_path.read_text(encoding="utf-8"), doc)

    doc.add_heading("Appendix C — Evaluation figures", level=1)
    for name, caption in [
        ("binary_confusion_matrix.png", "Figure C1. Binary confusion matrix (IID test sample)"),
        ("binary_roc.png", "Figure C2. Binary ROC curve (IID)"),
        ("multiclass_confusion_matrix.png", "Figure C3. Multiclass confusion matrix (IID, six attack classes)"),
        ("feature_importance.png", "Figure C4. Top feature importances"),
        ("temporal_binary_iid_vs_holdout.png", "Figure C5. Binary metrics: IID vs Friday vs Mon–Thu samples (superseded P10 slice: contaminated by training rows, ML-3; historical record only, do not cite)"),
        ("temporal_multiclass_iid_vs_holdout.png", "Figure C6. Multiclass: IID (6-class) vs Friday subset (superseded P10 slice: contaminated by training rows, ML-3; historical record only, do not cite)"),
        ("temporal_friday_multiclass_confusion.png", "Figure C7. Friday temporal multiclass confusion matrix (present families) (superseded P10 slice: contaminated by training rows, ML-3; historical record only, do not cite)"),
        ("temporal_friday_classwise.png", "Figure C8. Friday temporal class-wise support vs F1 (superseded P10 slice: contaminated by training rows, ML-3; historical record only, do not cite)"),
        ("temporal_generalization_summary.png", "Figure C9. Temporal generalization summary card (superseded P10 slice: contaminated by training rows, ML-3; historical record only, do not cite)"),
        ("drift_psi_train_vs_test.png", "Figure C10. Feature PSI train→test (IID drift check)"),
        ("drift_label_distribution.png", "Figure C11. Label distribution train vs test (IID)"),
        ("error_binary_fp_fn_counts.png", "Figure C12. Binary FP/FN residual counts (IID test)"),
        ("error_multiclass_top_confusions.png", "Figure C13. Top multiclass residual confusions"),
        ("drift_error_research_summary.png", "Figure C14. Drift + error research summary card"),
        ("model_binary_selection_scores.png", "Figure C15. Binary multi-objective selection scores"),
        ("model_binary_f1_vs_recall.png", "Figure C16. Binary F1 vs recall trade-off (why DT over XGB)"),
        ("model_binary_metric_bars.png", "Figure C17. Binary validation metric bars"),
        ("model_multiclass_selection.png", "Figure C18. Multiclass RF vs XGB selection"),
        ("model_selection_summary.png", "Figure C19. Model selection summary card"),
    ]:
        path = figures / name
        if path.exists():
            doc.add_picture(str(path), width=Inches(5.5))
            cap = doc.add_paragraph(caption)
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if cap.runs:
                cap.runs[0].italic = True
        else:
            miss = doc.add_paragraph(f"[Missing figure: {name}]")
            if miss.runs:
                miss.runs[0].italic = True

    research_figs = ROOT / "docs" / "research" / "paper_build" / "figs"
    doc.add_heading("Appendix D — Open-set research figures (Chapter 13)", level=1)
    for name, caption in [
        ("fig2_aegis_osr.png", "Figure D1. The Aegis-OSR gate: two evidence scores become benign surprisals, are summed "
                               "(Fisher fusion) and converted to a split-conformal p-value; alerts are attributed by a "
                               "class-conditional conformal test."),
        ("fig3_loafo_by_family.png", "Figure D2. Zero-day recall at α = 1% for each withheld family (LOAFO, mean and 95% "
                                     "CI over five seeds)."),
        ("fig4_operating_curve.png", "Figure D3. Zero-day recall against the benign false-alarm budget α (LOAFO, mean "
                                     "over five seeds)."),
        ("fig5_adaptation.png", "Figure D4. Label-light recalibration under temporal shift: realised benign "
                                "false-positive rate (top) and zero-day recall (bottom)."),
        ("fig6_gate.png", "Figure D5. Operating points of the deployed Zero-Day Gate: realised benign false-positive "
                          "rate against the nominal α."),
    ]:
        path = research_figs / name
        if path.exists():
            doc.add_picture(str(path), width=Inches(5.5))
            cap = doc.add_paragraph(caption)
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if cap.runs:
                cap.runs[0].italic = True
        else:
            miss = doc.add_paragraph(f"[Missing figure: {name}]")
            if miss.runs:
                miss.runs[0].italic = True

    doc.save(out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
