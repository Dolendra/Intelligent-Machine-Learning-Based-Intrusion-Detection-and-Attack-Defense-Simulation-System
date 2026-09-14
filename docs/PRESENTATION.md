# Aegis IDS — Viva / Presentation Outline (8–12 slides)

Use this as a PowerPoint/Google Slides skeleton. Keep each slide sparse; demo live where marked.  
**Frozen models (v1.1):** Binary **Decision Tree** @ **0.85** · Multiclass **Random Forest** (six attack families, no BENIGN).

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
- Features: StandardScaler + SelectKBest(**f_classif**, k=40)

## Slide 6 — Two-stage ML (RQ1)
- Stage 1: Benign vs Attack → **Decision Tree** (threshold **0.85**)
- Stage 2: Attack family (attack-only) → **Random Forest**
- Families: Bot · BruteForce · DDoS · DoS · PortScan · WebAttack
- Test (binary): F1 **0.99048** · ROC-AUC **0.99916** · Recall **0.997**
- Test (multiclass): macro-F1 **0.99813** · weighted-F1 **0.99979**
- Note: benchmark IID metrics ≠ live-deployment guarantees

## Slide 7 — Why metrics matter
- Imbalanced data → recall/precision/F1 over accuracy
- Multi-objective binary selection (not raw F1 alone)
- Show confusion matrix + ROC figures

## Slide 8 — Explainability (RQ2/RQ3)
- SHAP primary · LIME secondary
- Live: Detection → Why? tabs

## Slide 9 — Risk & recommendations (RQ4)
- Risk weights: 50% attack · 25% confidence · 15% intensity · 10% asset
- Advisory playbooks (not auto-blocking)

## Slide 10 — Simulation (RQ5) **[LIVE DEMO]**
- Topology · attack surge · IDS alert · defense · recover
- Safety: visualization only; efficacy values are assumptions

## Slide 11 — Contribution & limitations
- Contribution: **integration**, not a new algorithm claim
- Limits: CICIDS age, sim is pedagogical, rule-based recs, no live capture in research baseline

## Slide 12 — Q&A
- Point to `docs/DEMO.md` talking points
- Frozen artifacts: `model_metadata.json` / `training_report.json`

---

## Timing guide
| Segment | Time |
|---------|------|
| Slides 1–6 | 3 min |
| Live demo | 3–4 min |
| Slides 11–12 | 1 min |
| Buffer / questions | rest |
