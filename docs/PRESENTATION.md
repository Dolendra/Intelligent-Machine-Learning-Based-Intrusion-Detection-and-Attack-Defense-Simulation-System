# Aegis IDS — Viva / Presentation Outline (15 slides)

Use this as a PowerPoint/Google Slides skeleton, or regenerate:

```bash
python scripts/08_export_presentation_pptx.py
# → docs/Aegis_IDS_Viva_Presentation.pptx
```

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

## Slide 7 — Why metrics & selection matter
- Imbalanced data → recall/precision/F1 over accuracy
- Multi-objective binary selection (recall 0.30 …) — **not raw F1 alone**
- XGBoost can win F1; Decision Tree wins **recall** → selected
- Show `model_binary_f1_vs_recall.png` + confusion / ROC figures

## Slide 8 — Temporal generalization **[RESEARCH]**
- Protocol: score **frozen** DT/RF on day-named CSV samples (no retrain)
- Friday holdout: n=36k, attack rate ≈34% → binary F1 **0.9977**
- Mon–Thu sample: n=60k, attack rate ≈7% → binary F1 **0.9800** (mild drop)
- Multiclass Friday: only **Bot / DDoS / PortScan** present — not a 6-class temporal claim
- Figures: `temporal_binary_iid_vs_holdout.png`, `temporal_generalization_summary.png`
- Message: IID strength ≠ automatic temporal / live generalization

## Slide 9 — Drift & residual errors **[RESEARCH]**
- IID train→test drift: **0** features with PSI ≥ 0.2 (expected under stratified same-corpus split)
- Binary residuals: FP **1,377** · FN **255** (FPR 0.00329 / FNR 0.00300)
- Multiclass: **18** errors / 85,139 attacks — mainly PortScan / DoS / WebAttack
- Message: PSI≈0 ≠ live drift absence; residual family confusions remain

## Slide 10 — Explainability (RQ2/RQ3)
- SHAP primary · LIME secondary
- Live: Detection → Why? tabs

## Slide 11 — Risk & recommendations (RQ4)
- Risk weights: 50% attack · 25% confidence · 15% intensity · 10% asset
- Advisory playbooks (not auto-blocking)

## Slide 12 — Simulation (RQ5) **[LIVE DEMO]**
- Topology · attack surge · IDS alert · defense · recover
- Safety: visualization only; efficacy values are assumptions

## Slide 13 — Limitations & threats to validity
- CICIDS2017 age / scenario structure (not continuous enterprise traffic)
- Temporal slices are capped samples; multiclass temporal coverage incomplete
- IID drift check ≠ temporal/live/cross-dataset drift
- Simulation efficacy = assumptions; recommendations = advisory
- **External-dataset validation = future work** (not fabricated)
- Not a claim of production IDS readiness

## Slide 14 — Contribution
- Contribution: **integration** + honest evaluation framing, not a new algorithm claim
- Research baseline frozen; Stage-2 productionization is a separate track

## Slide 15 — Q&A
- Point to `docs/DEMO.md` + `docs/VIVA_QA.md`
- Frozen artifacts: `model_metadata.json` / `training_report.json` / `temporal_holdout_report.json` / `drift_report.json`

---

## Timing guide
| Segment | Time |
|---------|------|
| Slides 1–7 | 3 min |
| Slides 8–9 (temporal + drift/errors) | 1.5 min |
| Live demo | 3–4 min |
| Slides 13–15 | 1–2 min |
| Buffer / questions | rest |
