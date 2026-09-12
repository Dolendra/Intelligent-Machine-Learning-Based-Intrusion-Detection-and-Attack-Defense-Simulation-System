# Aegis IDS — Viva / Presentation Outline (8–12 slides)

Use this as a PowerPoint/Google Slides skeleton. Keep each slide sparse; demo live where marked.

---

## Slide 1 — Title
- **Aegis IDS**
- Intelligent ML-Based Intrusion Detection & Attack–Defense Simulation
- Team members · College · Year

## Slide 2 — Problem
- Classic IDS: “Attack detected”
- Analyst still needs: type · why · severity · action · visual understanding

## Slide 3 — Solution (one sentence)
> Detect → Classify → Explain → Assess risk → Recommend → Simulate attack/defense

## Slide 4 — Architecture
- React UI ↔ FastAPI ↔ ML + Risk + Recs + Simulation ↔ CICIDS2017 / SQLite
- Diagram from README

## Slide 5 — Dataset & prep
- CICIDS2017 MachineLearningCVE
- Clean · normalize labels · rare-class filter · stratified split
- ~2.52M flows after cleaning

## Slide 6 — Two-stage ML (RQ1)
- Stage 1: Benign vs Attack
- Stage 2: Attack family
- Best model: **XGBoost**
- Test: Binary F1 **0.993** · ROC-AUC **0.9999** · Multiclass weighted F1 **0.998**

## Slide 7 — Why metrics matter
- Imbalanced data → recall/precision/F1 over accuracy
- Show confusion matrix + ROC figures

## Slide 8 — Explainability (RQ2/RQ3)
- SHAP primary · LIME secondary
- Live: Detection → Why? tabs

## Slide 9 — Risk & recommendations (RQ4)
- Configurable severity bands
- Advisory playbooks (not auto-blocking)

## Slide 10 — Simulation (RQ5) **[LIVE DEMO]**
- Topology · attack surge · IDS alert · defense · recover
- Safety: visualization only

## Slide 11 — Contribution & limitations
- Contribution: **integration**, not a new algorithm claim
- Limits: CICIDS age, sim is pedagogical, rule-based recs

## Slide 12 — Q&A
- Point to `docs/DEMO.md` talking points

---

## Timing guide
| Segment | Time |
|---------|------|
| Slides 1–6 | 3 min |
| Live demo | 3–4 min |
| Slides 11–12 | 1 min |
| Buffer / questions | rest |
