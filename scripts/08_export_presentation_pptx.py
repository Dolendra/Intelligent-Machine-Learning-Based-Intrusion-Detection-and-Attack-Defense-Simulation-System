"""Generate viva PowerPoint aligned to frozen v1.1 (Decision Tree + Random Forest)."""
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
        box2 = slide.shapes.add_textbox(Inches(0.6), Inches(1.1), Inches(12), Inches(0.55))
        p2 = box2.text_frame.paragraphs[0]
        r2 = p2.add_run()
        r2.text = subtitle
        _set_run(r2, 15, False, MUTED)


def bullets(slide, lines: list[str], top=1.85, left=0.7, width=12, size=20):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(5.2))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = 0
        run = p.add_run()
        run.text = "•  " + line
        _set_run(run, size, False, TEXT)
        p.space_after = Pt(8)


def add_pic(slide, name: str, left: float, top: float, height: float | None = None, width: float | None = None):
    path = FIGS / name
    if not path.exists():
        return
    kwargs = {}
    if height is not None:
        kwargs["height"] = Inches(height)
    if width is not None:
        kwargs["width"] = Inches(width)
    slide.shapes.add_picture(str(path), Inches(left), Inches(top), **kwargs)


def main() -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 1 Title
    s = add_blank(prs)
    box = s.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.5), Inches(4))
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
    r3.text = "\nFrozen v1.1  ·  Decision Tree @ 0.85  ·  Random Forest (attack-only)"
    _set_run(r3, 16, False, MUTED)
    p4 = tf.add_paragraph()
    p4.alignment = PP_ALIGN.CENTER
    r4 = p4.add_run()
    r4.text = "Team members  ·  College  ·  Year"
    _set_run(r4, 14, False, MUTED)

    # 2 Problem
    s = add_blank(prs)
    title_block(s, "Problem", "Why a classic IDS alert is not enough")
    bullets(
        s,
        [
            "Typical IDS output: “Attack detected.”",
            "Analysts still need: attack type · why · severity · recommended action",
            "Evaluators also need a visual attack → defense story",
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
            "Platform: Aegis IDS (prototype / decision-support)",
            "Contribution: integration + honest evaluation — not a new IDS algorithm claim",
            "Safety: no live capture claim · no automatic network blocking",
        ],
        size=22,
    )

    # 4 Architecture
    s = add_blank(prs)
    title_block(s, "Architecture")
    bullets(
        s,
        [
            "React UI  ↔  FastAPI  ↔  ML + Risk + Recommendations + Simulation",
            "Data: CICIDS2017 MachineLearningCVE · trained models · SQLite incidents",
            "Two-stage ML: binary then attack-family multiclass (no BENIGN in Stage-2)",
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
            "StandardScaler + SelectKBest(f_classif, k=40) fit on train only",
            "Attack families: Bot · BruteForce · DDoS · DoS · PortScan · WebAttack",
        ],
    )

    # 6 ML results
    s = add_blank(prs)
    title_block(s, "Two-stage ML results (RQ1)", "Binary: Decision Tree @ 0.85  ·  Multiclass: Random Forest")
    bullets(
        s,
        [
            "Binary test: F1 0.99048 · Recall 0.997 · ROC-AUC 0.99916 · FPR 0.00329",
            "Multiclass test: macro-F1 0.99813 · weighted-F1 0.99979 · accuracy 0.99979",
            "Candidates compared: LR, Decision Tree, Random Forest, XGBoost",
            "IID benchmark strength ≠ live-deployment performance guarantee",
        ],
        size=19,
    )

    # 7 Selection / metrics
    s = add_blank(prs)
    title_block(s, "Why Decision Tree (not XGBoost)?", "Multi-objective selection — recall first")
    bullets(
        s,
        [
            "Weights: recall 0.30 · F1 0.25 · PR-AUC 0.20 · FPR 0.15 · latency 0.10",
            "XGBoost can win raw F1; Decision Tree wins attack recall → selected",
            "Multiclass: Random Forest edges XGBoost on macro/weighted blend",
            "For IDS, missed attacks (FN) are costly — policy matters",
        ],
        left=0.6,
        width=6.5,
        size=18,
    )
    add_pic(s, "model_binary_f1_vs_recall.png", 7.2, 1.9, width=5.6)

    # 8 Evaluation figures
    s = add_blank(prs)
    title_block(s, "Evaluation figures", "IID test confusion matrix & ROC")
    add_pic(s, "binary_confusion_matrix.png", 0.5, 1.7, height=5.0)
    add_pic(s, "binary_roc.png", 6.9, 1.7, height=5.0)

    # 9 Temporal
    s = add_blank(prs)
    title_block(s, "Temporal generalization", "Frozen models · day-aware Friday holdout · no retrain")
    bullets(
        s,
        [
            "Friday sample (n=36k, attack rate ~34%): binary F1 0.9977",
            "Mon–Thu sample (n=60k, ~7% attacks): binary F1 0.980 — mild drop",
            "Friday multiclass only Bot/DDoS/PortScan — not a 6-class temporal claim",
            "Message: IID strength ≠ automatic temporal / live generalization",
        ],
        left=0.6,
        width=6.6,
        size=17,
    )
    add_pic(s, "temporal_generalization_summary.png", 7.1, 1.85, width=5.7)

    # 10 Drift + errors
    s = add_blank(prs)
    title_block(s, "Drift & residual errors", "IID monitoring + confusion structure")
    bullets(
        s,
        [
            "Train→test IID drift: 0 features with PSI ≥ 0.2 (expected same-corpus)",
            "Binary residuals: FP 1,377 · FN 255 (FPR 0.00329 / FNR 0.00300)",
            "Multiclass: 18 errors / 85,139 attacks — PortScan / DoS / WebAttack",
            "PSI≈0 ≠ live drift absence · external dataset = future work",
        ],
        left=0.6,
        width=6.6,
        size=17,
    )
    add_pic(s, "error_multiclass_top_confusions.png", 7.1, 1.85, width=5.7)

    # 11 XAI
    s = add_blank(prs)
    title_block(s, "Explainability (RQ2 / RQ3)")
    bullets(
        s,
        [
            "SHAP: feature contributions for each prediction (primary)",
            "LIME: local surrogate explanation (secondary)",
            "Live demo: Detection → Why? → SHAP / LIME tabs",
            "Decision support — not treated as causal proof",
        ],
        left=0.6,
        width=6.5,
        size=18,
    )
    add_pic(s, "feature_importance.png", 7.2, 1.9, width=5.5)

    # 12 Risk
    s = add_blank(prs)
    title_block(s, "Risk & recommendations (RQ4)")
    bullets(
        s,
        [
            "Risk weights: 50% attack base · 25% confidence · 15% intensity · 10% asset",
            "Severity bands: LOW / MEDIUM / HIGH / CRITICAL (project conventions)",
            "Playbooks: rate limiting, filtering, WAF, isolation, …",
            "Advisory only — platform does not auto-block real networks",
        ],
    )

    # 13 Simulation
    s = add_blank(prs)
    title_block(s, "Simulation (RQ5) — LIVE DEMO", "Attack → Detect → Defend → Recover")
    bullets(
        s,
        [
            "Topology: Attacker → Firewall → Router → Server / PCs + IDS",
            "Step: normal → attack → impact → IDS alert → defense → recovery",
            "Defense effectiveness values are simulation assumptions",
            "Safety: controlled visualization only — no real cyberattacks",
        ],
        size=20,
    )

    # 14 Limitations
    s = add_blank(prs)
    title_block(s, "Limitations & threats to validity")
    bullets(
        s,
        [
            "CICIDS2017 age / scenario structure ≠ continuous enterprise traffic",
            "Temporal slices are capped samples; multiclass temporal coverage incomplete",
            "IID drift check ≠ temporal / live / cross-dataset drift",
            "External-dataset validation not performed — stated as future work",
            "Not a claim of production IDS readiness",
        ],
        size=18,
    )

    # 15 Contribution + Q&A
    s = add_blank(prs)
    title_block(s, "Contribution")
    bullets(
        s,
        [
            "Integrated ML-IDS decision-support + visualization platform",
            "Honest evaluation: IID · temporal · drift · residual errors · model selection",
            "Research baseline frozen; Stage-2 productionization is a separate track",
        ],
        top=1.8,
        size=20,
    )
    box = s.shapes.add_textbox(Inches(0.7), Inches(5.2), Inches(12), Inches(1.5))
    tf = box.text_frame
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = "Questions?   ·   docs/DEMO.md   ·   docs/VIVA_QA.md   ·   docs/Aegis_IDS_Project_Report.docx"
    _set_run(r, 16, False, MUTED)

    prs.save(OUT)
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
