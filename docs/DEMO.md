# Aegis IDS — Demo & Viva Script (~2–3 minutes)

## One-sentence answer

> We are building an intelligent machine-learning-based intrusion detection platform that detects and classifies network attacks, explains the reasons behind its predictions, assesses their risk, recommends appropriate defensive actions, and interactively simulates the attack-to-defense lifecycle through a visual network environment.

## Live demo flow (follow exactly)

1. Open **http://127.0.0.1:5173/** — Dashboard shows incident analytics.
   - Mention auto-refresh (WebSocket / polling) updates the overview — still **not** live packet capture.
2. Go to **Detection**
   - Demo flow type: `DDoS` → **Load sample flow** → **Detect & classify**
   - Point to: verdict, confidence, certainty band, risk/severity, recommendation, **rules fired**
   - Point to **WHY DID AEGIS DO THIS?** decision trace (traffic → ML → risk → recommendation → incident)
   - Scroll to **Why?** — show SHAP (and that fallback is labeled if used)
   - Click **Simulate this incident** (hands off to Simulation with that session)
   - Optional: **Batch sample** or **Upload CSV** for multi-flow analytics
3. Go to **Simulation**
   - Configure intensity/confidence if desired, then **Run simulation** / **Play**
   - Point to detection/defense/recovery delays and without-vs-with defense table
   - Say: “Controlled visualization only — not a real attack tool.”
4. Go to **Reports** / **Incident detail**
   - Show lifecycle timeline + decision trace
   - Optional: **Export CSV / JSON / PDF**
5. Optional: **Models** page — health, threshold, validation comparison table

## Likely viva questions

| Question | Answer cue |
|----------|------------|
| Why two-stage ML? | Binary detection first, then attack-family classification — clearer academically and operationally |
| Why not accuracy alone? | Class imbalance; we report recall/precision/F1, PR-AUC, FPR/FNR |
| Why SHAP? | Turns “model said attack” into feature-level decision support; LIME is secondary |
| Do you auto-block traffic? | No — recommendations are advisory only |
| Dataset? | CICIDS2017 (`MachineLearningCVE`), cleaned, rare classes filtered, stratified split |
| Confidence vs risk? | Confidence is model certainty; risk is impact-oriented scoring (attack family + confidence + intensity + asset criticality) |
| Novelty? | Integration: ML + XAI + risk + rules + recommendation + simulation — not a new algorithm claim |

## Team talking points

- **Member 1:** data prep, dual feature selection, model comparison, calibration/HPO experiments
- **Member 2:** SHAP/LIME, risk bands, rule engine, recommendations, incidents lifecycle
- **Member 3:** FastAPI, React UI, React Flow simulation, WebSocket dashboard, exports

Everyone should still be able to narrate the full pipeline end-to-end.

## Honest wording (use these)

Prefer: **ML-based intrusion detection prototype**, **controlled attack–defense simulation**, **decision-support recommendations**.
