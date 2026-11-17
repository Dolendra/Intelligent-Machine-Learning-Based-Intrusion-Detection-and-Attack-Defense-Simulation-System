"""Small python-docx helper layer: headings, rich paragraphs, OMML equations, tables, figures."""
from __future__ import annotations

import copy
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, Cm, RGBColor
from latex2mathml.converter import convert as tex2mml
from lxml import etree

_XSL = etree.XSLT(etree.parse(r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL"))
FONT = "Times New Roman"
_SUBS = [(k, k.split("_", 1)[0] + "_{" + k.split("_", 1)[1] + "}") for k in (
    "s_sup", "s_nov", "t_sup", "t_nov", "t_inf", "μ_i", "σ_i", "τ_j", "α_fam", "w_b", "w_c", "w_i", "w_a",
    "B_k", "a_pre", "a_post", "AUROC_u", "t_j", "n_c", "n_max", "NN_j")]
_SUBS.insert(0, ("s_j^{max}", "s_{j}^{max}"))
_SUBS.append(("s_j", "s_{j}"))
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII"]


def omml(latex: str):
    mml = tex2mml(latex)
    res = _XSL(etree.fromstring(mml.encode("utf-8")))
    return copy.deepcopy(res.getroot())


class Paper:
    def __init__(self) -> None:
        self.doc = Document()
        self.sec = 0
        self.sub = 0
        self.eq = 0
        self.tab = 0
        self.fig = 0
        self.labels: dict[str, str] = {}
        s = self.doc.sections[0]
        s.page_height, s.page_width = Cm(29.7), Cm(21.0)
        s.left_margin = s.right_margin = Cm(2.2)
        s.top_margin = s.bottom_margin = Cm(2.2)
        self.text_width = s.page_width - s.left_margin - s.right_margin
        st = self.doc.styles["Normal"]
        st.font.name = FONT
        st.font.size = Pt(10.5)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        pf = st.paragraph_format
        pf.space_after = Pt(4)
        pf.line_spacing = 1.12
        self._page_numbers()

    # ------------------------------------------------------------------ basics
    def _page_numbers(self) -> None:
        p = self.doc.sections[0].footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        for t, txt in (("begin", None), (None, "PAGE"), ("end", None)):
            if t:
                el = OxmlElement("w:fldChar"); el.set(qn("w:fldCharType"), t); run._r.append(el)
            else:
                el = OxmlElement("w:instrText"); el.set(qn("xml:space"), "preserve"); el.text = txt; run._r.append(el)
        run.font.size = Pt(9)

    def _runs(self, p, text: str, size: float | None = None, base_italic=False):
        """Inline markup: **bold**, *italic*, $latex$ (inline OMML), ^{sup}, _{sub}."""
        for a, z in _SUBS:
            text = text.replace(a, z)
        tokens = re.split(r"(\*\*.+?\*\*|\*.+?\*|\$.+?\$|\^\{.+?\}|_\{.+?\})", text)
        for tok in tokens:
            if not tok:
                continue
            if tok.startswith("$") and tok.endswith("$"):
                p._p.append(omml(tok[1:-1]))
                continue
            bold = tok.startswith("**")
            ital = (tok.startswith("*") and not bold) or base_italic
            sup = tok.startswith("^{")
            sub = tok.startswith("_{")
            body = tok[2:-2] if bold else tok[1:-1] if tok.startswith("*") else tok[2:-1] if (sup or sub) else tok
            r = p.add_run(body)
            r.bold = bold or None
            r.italic = ital or None
            if sup:
                r.font.superscript = True
            if sub:
                r.font.subscript = True
            if size:
                r.font.size = Pt(size)
        return p

    def para(self, text: str, *, align="justify", indent=True, size=None, italic=False, space_after=4, keep=False):
        p = self.doc.add_paragraph()
        p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                       "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
        if indent:
            p.paragraph_format.first_line_indent = Cm(0.5)
        p.paragraph_format.space_after = Pt(space_after)
        if keep:
            p.paragraph_format.keep_with_next = True
        self._runs(p, text, size, italic)
        return p

    def bullets(self, items: list[str]):
        for it in items:
            p = self.doc.add_paragraph(style="List Bullet")
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(2)
            self._runs(p, it)

    def numbered(self, items: list[str]):
        for i, it in enumerate(items, 1):
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.left_indent = Cm(0.9)
            p.paragraph_format.first_line_indent = Cm(-0.5)
            p.paragraph_format.space_after = Pt(2)
            self._runs(p, f"{i})\u2002" + it)

    # ------------------------------------------------------------------ headings
    def section(self, title: str):
        self.sub = 0
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.keep_with_next = True
        if title.lower() in ("references", "acknowledgment", "appendix", "data and code availability",
                             "author contributions", "declaration of competing interest"):
            label = title.upper()
        else:
            label = f"{ROMAN[self.sec]}. {title.upper()}"
            self.sec += 1
        r = p.add_run(label)
        r.font.size = Pt(10.5)
        r.font.small_caps = True
        r.bold = False
        return p

    def subsection(self, title: str):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(f"{chr(65 + self.sub)}. {title}")
        r.italic = True
        self.sub += 1
        return p

    def runin(self, head: str, text: str):
        """Run-in paragraph heading (IEEE third level)."""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Cm(0.5)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(head + ": ")
        r.italic = True
        self._runs(p, text)
        return p

    # ------------------------------------------------------------------ equations
    def equation(self, latex: str, label: str | None = None):
        """Display equation in a borderless 2-cell table: centred math | right-aligned number."""
        self.eq += 1
        if label:
            self.labels[label] = str(self.eq)
        tbl = self.doc.add_table(rows=1, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        c0, c1 = tbl.rows[0].cells
        c0.width = int(self.text_width * 0.90)
        c1.width = int(self.text_width * 0.10)
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_before = Pt(2)
        p0.paragraph_format.space_after = Pt(2)
        para = OxmlElement("m:oMathPara")
        para.append(omml(latex))
        p0._p.append(para)
        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p1.add_run(f"({self.eq})")
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
        c0.vertical_alignment = c1.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        return self.eq

    # ------------------------------------------------------------------ tables
    def _cell_border(self, cell, **edges):
        tcPr = cell._tc.get_or_add_tcPr()
        borders = tcPr.find(qn("w:tcBorders"))
        if borders is None:
            borders = OxmlElement("w:tcBorders"); tcPr.append(borders)
        for edge, val in edges.items():
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single" if val else "nil")
            if val:
                el.set(qn("w:sz"), str(val)); el.set(qn("w:color"), "000000")
            borders.append(el)

    def table(self, caption: str, header: list[str], rows: list[list[str]], *, widths: list[float] | None = None,
              label: str | None = None, size: float = 8.5, notes: str | None = None, bold_rows=(), group_rows=()):
        self.tab += 1
        if label:
            self.labels[label] = ROMAN[self.tab - 1]
        cap = self.doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_before = Pt(6)
        cap.paragraph_format.space_after = Pt(1)
        cap.paragraph_format.keep_with_next = True
        r = cap.add_run(f"TABLE {ROMAN[self.tab - 1]}")
        r.font.size = Pt(8.5)
        cap2 = self.doc.add_paragraph()
        cap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap2.paragraph_format.space_after = Pt(3)
        cap2.paragraph_format.keep_with_next = True
        r = cap2.add_run(caption.upper() if len(caption) < 0 else caption)
        r.font.size = Pt(8.5); r.italic = True
        t = self.doc.add_table(rows=1 + len(rows), cols=len(header))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for j, h in enumerate(header):
            c = t.rows[0].cells[j]
            c.text = ""
            self._runs(c.paragraphs[0], h, size)
            for run in c.paragraphs[0].runs:
                run.bold = True
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT
            self._cell_border(c, top=8, bottom=6)
        for i, row in enumerate(rows, 1):
            for j, v in enumerate(row):
                c = t.rows[i].cells[j]
                c.text = ""
                p = c.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                self._runs(p, str(v), size)
                if (i - 1) in bold_rows:
                    for run in p.runs:
                        run.bold = True
                if (i - 1) in group_rows:
                    for run in p.runs:
                        run.italic = True
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT
                if i == len(rows):
                    self._cell_border(c, bottom=8)
        for row in t.rows:
            row.cells[0].paragraphs[0].paragraph_format.keep_with_next = True
            trPr = row._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit"); trPr.append(cs)
        if widths:
            tot = sum(widths)
            for j, w in enumerate(widths):
                for row in t.rows:
                    row.cells[j].width = int(self.text_width * w / tot)
        if notes:
            n = self.doc.add_paragraph()
            n.paragraph_format.space_before = Pt(2)
            n.paragraph_format.space_after = Pt(6)
            self._runs(n, notes, 7.5)
        else:
            self.doc.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    # ------------------------------------------------------------------ figures
    def figure(self, path: Path, caption: str, width_frac: float = 0.95, label: str | None = None):
        self.fig += 1
        if label:
            self.labels[label] = str(self.fig)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(6)
        p.add_run().add_picture(str(path), width=int(self.text_width * width_frac))
        c = self.doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        c.paragraph_format.space_after = Pt(8)
        r = c.add_run(f"Fig. {self.fig}. ")
        r.font.size = Pt(8.5)
        self._runs(c, caption, 8.5)
        return self.fig

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def save(self, path: Path):
        self.doc.save(str(path))
