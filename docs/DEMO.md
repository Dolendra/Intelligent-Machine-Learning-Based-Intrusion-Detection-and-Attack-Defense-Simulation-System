# Aegis IDS — Demo & Viva Script (~2 minutes)

## One-sentence answer

> We are building an intelligent machine-learning-based intrusion detection platform that detects and classifies network attacks, explains the reasons behind its predictions, assesses their risk, recommends appropriate defensive actions, and interactively simulates the attack-to-defense lifecycle through a visual network environment.

## Live demo flow (follow exactly)

1. Open **http://127.0.0.1:5173/** — Dashboard shows seeded incidents.
2. Go to **Detection**
   - Demo flow type: `DDoS` → **Load sample flow** → **Detect & classify**
   - Point to: verdict, confidence, risk/severity, recommendation
   - Scroll to **Why? (SHAP)** — name the top 2 features
3. Go to **Simulation**
   - New scenario `DDoS` → press **Next state** through attack → detection
   - **Apply defense** → show blocked edge / recovered service
   - Say: “This is a controlled visualization, not a real attack tool.”
4. Go to **Reports** — show logged / seeded incidents

## Likely viva questions

| Question | Answer cue |
|----------|------------|
| Why two-stage ML? | Binary detection first, then attack-family classification — clearer academically and operationally |
| Why not accuracy alone? | Class imbalance; we prioritize recall/precision/F1 on attacks |
| Why SHAP? | Turns “model said attack” into feature-level decision support |
| Do you auto-block traffic? | No — recommendations are advisory only |
| Dataset? | CICIDS2017 (`MachineLearningCVE`), cleaned, rare classes filtered, stratified split |
| Novelty? | Integration: ML + XAI + risk + recommendation + simulation — not a new algorithm claim |

## Team talking points

- **Member 1:** data prep, features, model comparison, metrics in `training_report.json`
- **Member 2:** SHAP, risk bands, recommendation mapping, incidents DB
- **Member 3:** FastAPI, React UI, React Flow simulation

Everyone should still be able to narrate the full pipeline end-to-end.
