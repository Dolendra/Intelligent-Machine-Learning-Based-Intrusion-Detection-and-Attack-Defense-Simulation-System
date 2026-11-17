"""Minimal Markdown → .docx converter for the project's guides (headings, paragraphs, bullet/numbered lists,
pipe tables, **bold**, *italic*, `code`, links). Usage: python md2docx.py input.md output.docx"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def runs(p, text: str, size: float | None = None, bold: bool = False) -> None:
    for tok in INLINE.split(text):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            r = p.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith("`") and tok.endswith("`"):
            r = p.add_run(tok[1:-1]); r.font.name = "Consolas"; r.font.size = Pt((size or 10.5) - 1)
        elif tok.startswith("[") and "](" in tok:
            label = tok[1:tok.index("](")]
            r = p.add_run(label); r.font.color.rgb = RGBColor(0x0F, 0x76, 0x6E); r.underline = True
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            r = p.add_run(tok[1:-1]); r.italic = True
        else:
            r = p.add_run(tok)
        if size:
            r.font.size = Pt(size)
        if bold:
            r.bold = True


def shade(cell, hex_fill: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def convert(md: str, out: Path) -> None:
    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(2.0)
    st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
    st.paragraph_format.space_after = Pt(4); st.paragraph_format.line_spacing = 1.12
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip() or line.strip() == "---":
            i += 1
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            h = doc.add_heading(level=min(level, 3))
            runs(h, line.lstrip("#").strip())
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            t = doc.add_table(rows=len(rows), cols=max(len(r) for r in rows))
            t.style = "Table Grid"
            for ri, r in enumerate(rows):
                for ci, c in enumerate(r):
                    cell = t.rows[ri].cells[ci]
                    cell.text = ""
                    runs(cell.paragraphs[0], c, 9, bold=(ri == 0))
                    if ri == 0:
                        shade(cell, "E6F2F1")
            doc.add_paragraph()
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            numbered = m.group(2)[0].isdigit()
            indent = len(m.group(1)) // 2
            p = doc.add_paragraph(style="List Number" if numbered else ("List Bullet 2" if indent else "List Bullet"))
            p.paragraph_format.space_after = Pt(2)
            runs(p, m.group(3))
            i += 1
            continue
        # paragraph: merge following non-special lines
        buf = [line.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||\s*([-*]|\d+\.)\s|---)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        runs(p, " ".join(buf))
    doc.save(str(out))


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    convert(src.read_text(encoding="utf-8"), dst)
    print("wrote", dst)
