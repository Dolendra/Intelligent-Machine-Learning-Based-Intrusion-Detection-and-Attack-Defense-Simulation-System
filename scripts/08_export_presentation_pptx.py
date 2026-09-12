"""Generate viva PowerPoint from docs/PRESENTATION.md content + evaluation figures."""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "models" / "trained_models" / "figures"
OUT = ROOT / "docs" / "Aegis_IDS_Viva_Presentation.pptx"

# Slate / cyan theme (matches UI)
BG = RGBColor(0x07, 0x11, 0x1A)
ACCENT = RGBColor(0x3E, 0xC7, 0xC2)
TEXT = RGBColor(0xE7, 0xF0, 0xF5)
MUTED = RGBColor(0x8F, 0xA6, 0xB5)


def _set_run(run, size=20, bold=False, color=TEXT):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = "Calibri"


def add_blank(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), prs.slide_width, prs.slide_height
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = BG
    shape.line.fill.background()
    spTree = slide.shapes._spTree
    sp = shape._element
    spTree.remove(sp)
    spTree.insert(2, sp)
    return slide


def title_block(slide, title: str, subtitle: str | None = None):
    box = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12), Inches(1.0))
    tf = box.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title
    _set_run(run, 32, True, ACCENT)
    if subtitle:
        box2 = slide.shapes.add_textbox(Inches(0.6), Inches(1.1), Inches(12), Inches(0.6))
        p2 = box2.text_frame.paragraphs[0]
        r2 = p2.add_run()
        r2.text = subtitle
        _set_run(r2, 16, False, MUTED)


def bullets(slide, lines: list[str], top=1.9, left=0.7, width=12, size=22):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(5.2))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = 0
        run = p.add_run()
        run.text = "•  " + line
        _set_run(run, size, False, TEXT)
        p.space_after = Pt(10)


def main() -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 1 Title
    s = add_blank(prs)
    box = s.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.5), Inches(3))
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "Aegis IDS"
    _set_run(r, 48, True, ACCENT)
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = "Intelligent ML-Based Intrusion Detection\n& Attack–Defense Simulation System"
    _set_run(r2, 24, False, TEXT)
    p3 = tf.add_paragraph()
    p3.alignment = PP_ALIGN.CENTER
    r3 = p3.add_run()
    r3.text = "\nTeam members  ·  College  ·  Year"
    _set_run(r3, 16, False, MUTED)

    # 2 Problem
    s = add_blank(prs)
    title_block(s, "Problem", "Why a classic IDS alert is not enough")
    bullets(
        s,
        [
            "Typical IDS output: “Attack detected.”",
            "Analysts still need: attack type · why · severity · recommended action",
            "Students/evaluators also need a visual attack → defense story",
            "Gap: detection alone ≠ security decision support",
        ],
    )

    # 3 Solution
    s = add_blank(prs)
    title_block(s, "Our solution (one pipeline)")
    bullets(
        s,
        [
            "Detect → Classify → Explain → Assess risk → Recommend → Simulate",
            "Platform name: Aegis IDS",
            "Contribution: integration framework — not a claim of a new IDS algorithm",
        ],
        size=24,
    )

    # 4 Architecture
    s = add_blank(prs)
    title_block(s, "Architecture")
    bullets(
        s,
        [
            "React UI  ↔  FastAPI  ↔  ML + Risk + Recommendations + Simulation",
            "Data: CICIDS2017 flows · trained models · SQLite incidents",
            "Two-stage ML: binary (benign vs attack) then attack-family multiclass",
            "XAI: SHAP (primary) + LIME (secondary)",
        ],
    )

    # 5 Dataset
    s = add_blank(prs)
    title_block(s, "Dataset & preprocessing", "CICIDS2017 MachineLearningCVE")
    bullets(
        s,
        [
            "Clean · normalize labels · drop rare classes (<50 samples)",
            "~2.52M flows after cleaning; stratified train/val/test",
            "Scaler + SelectKBest fit on train only (no leakage)",
            "Families: BENIGN, DoS, DDoS, PortScan, BruteForce, WebAttack, Bot",
        ],
    )

    # 6 ML results
    s = add_blank(prs)
    title_block(s, "Two-stage ML results (RQ1)", "Best model: XGBoost")
    bullets(
        s,
        [
            "Binary test: F1 ≈ 0.993 · Recall ≈ 0.990 · ROC-AUC ≈ 0.9999",
            "Multiclass test: weighted F1 ≈ 0.998 · macro F1 ≈ 0.917",
            "Compared LR, Decision Tree, Random Forest, XGBoost",
            "For IDS, recall/precision/F1 matter more than raw accuracy",
        ],
    )

    # 7 Metrics figures
    s = add_blank(prs)
    title_block(s, "Evaluation figures", "Confusion matrix & ROC")
    left = FIGS / "binary_confusion_matrix.png"
    right = FIGS / "binary_roc.png"
    if left.exists():
        s.shapes.add_picture(str(left), Inches(0.6), Inches(1.8), height=Inches(4.8))
    if right.exists():
        s.shapes.add_picture(str(right), Inches(6.8), Inches(1.8), height=Inches(4.8))

    # 8 XAI
    s = add_blank(prs)
    title_block(s, "Explainability (RQ2 / RQ3)")
    bullets(
        s,
        [
            "SHAP: feature contributions for each prediction (primary)",
            "LIME: local surrogate explanation (secondary)",
            "Live demo: Detection → Why? → SHAP / LIME tabs",
            "Supports analyst trust — not treated as causal proof",
        ],
    )
    fig = FIGS / "feature_importance.png"
    if fig.exists():
        s.shapes.add_picture(str(fig), Inches(7.2), Inches(2.0), width=Inches(5.5))

    # 9 Risk
    s = add_blank(prs)
    title_block(s, "Risk & recommendations (RQ4)")
    bullets(
        s,
        [
            "Risk blends attack-family base + confidence + traffic intensity",
            "Severity bands: LOW / MEDIUM / HIGH / CRITICAL (configurable)",
            "Playbooks: rate limiting, filtering, WAF, isolation, …",
            "Advisory only — platform does not auto-block real networks",
        ],
    )

    # 10 Simulation LIVE
    s = add_blank(prs)
    title_block(s, "Simulation (RQ5) — LIVE DEMO", "Attack → Detect → Defend → Recover")
    bullets(
        s,
        [
            "Simplified topology: Attacker → Firewall → Router → Server / PCs + IDS",
            "Step through: normal → attack → impact → IDS alert → defense → recovery",
            "Safety: controlled visualization only — no real cyberattacks",
            "Open UI → Simulation → New scenario → Next / Apply defense",
        ],
        size=22,
    )

    # 11 Contribution
    s = add_blank(prs)
    title_block(s, "Contribution & limitations")
    bullets(
        s,
        [
            "Contribution: integrated decision-support + visualization for ML-IDS",
            "Limits: CICIDS2017 age / concept drift; pedagogical simulator",
            "Limits: rule-mapped recommendations (not learned policies)",
            "Future: live PCAP→flows, PostgreSQL, analyst feedback loop",
        ],
    )

    # 12 Q&A
    s = add_blank(prs)
    box = s.shapes.add_textbox(Inches(0.8), Inches(2.6), Inches(11.5), Inches(2.5))
    tf = box.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "Questions?"
    _set_run(r, 48, True, ACCENT)
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = "Demo script: docs/DEMO.md   ·   Report: docs/Aegis_IDS_Project_Report.docx"
    _set_run(r2, 16, False, MUTED)

    prs.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
