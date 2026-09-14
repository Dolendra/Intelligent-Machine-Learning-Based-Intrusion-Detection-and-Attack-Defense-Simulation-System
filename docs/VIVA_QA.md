# Aegis IDS — Viva Q&A Pack (frozen v1.1)

Use short answers first; expand only if asked. Cite artifacts when useful: `model_metadata.json`, `training_report.json`, `temporal_holdout_report.json`, `drift_report.json`.

---

## ML

### Why Decision Tree for binary?
Selected by **multi-objective** validation score (recall 0.30, F1 0.25, PR-AUC 0.20, FPR 0.15, latency 0.10). DT has higher **recall** than XGBoost; XGB can win raw F1. See `MODEL_COMPARISON.md`.

### Why Random Forest for multiclass?
Attack-only Stage-2; selection ≈ `0.7·macro-F1 + 0.3·weighted-F1`. RF edged XGB on the freeze validation scores.

### Why two-stage detection?
Binary **BENIGN vs ATTACK** first (IDS alert), then family classification **without BENIGN** — clearer operationally and academically than one flat multiclass including benign.

### Why 40 features / `f_classif`?
`SelectKBest(f_classif, k=40)` dual selectors fit **on train only** — reduces dimensionality, limits leakage. Not mutual-info in the freeze.

### Why not XGBoost as the final binary model?
Compared, not ignored. Higher F1 but lower recall under our IDS policy → not selected.

### Why threshold = 0.85?
Operating point from threshold research (`threshold_operating_point.json`); balances precision/recall for the freeze. Certainty band **[0.10, 0.95]** is separate from the decision threshold.

### Why is calibration disabled?
Sample isotonic calibration improved ECE slightly but hurt Brier and recall — research decision to keep `use_calibrated_binary: false`.

### What are the final test numbers?
Binary DT: F1 **0.99048**, recall **0.997**, ROC-AUC **0.99916**, FPR **0.00329**, FNR **0.00300**.  
Multiclass RF: accuracy **0.99979**, macro-F1 **0.99813**, weighted-F1 **0.99979**.

### Do these numbers guarantee real-world performance?
**No.** CICIDS2017 is a benchmark; IID splits overstate similarity to live traffic. We also report temporal holdout and residual errors.

---

## Cybersecurity

### What is an IDS?
Monitors traffic/hosts for malicious activity and raises alerts. Ours is a **network-flow ML IDS prototype** (offline CICIDS features), not a signature appliance.

### Signature vs anomaly / ML?
Signatures match known patterns (precise, brittle). ML/anomaly generalize from features but need careful evaluation and can false-alarm.

### NIDS vs HIDS?
Network IDS watches traffic; host IDS watches endpoints. Aegis is NIDS-style (flow features).

### Attack families we classify?
Bot, BruteForce, DDoS, DoS, PortScan, WebAttack (Infiltration/Heartbleed filtered as rare).

### Do you block attacks automatically?
**No.** Recommendations and simulation are **advisory / visualization only**.

---

## XAI

### Why SHAP?
Primary local explanation: which features pushed the prediction. Improves analyst trust; does **not** prove causality.

### Why LIME?
Secondary local linear surrogate for complementary intuition.

### What if SHAP fails?
UI/API should surface fallback/error labeling — explanation is decision-support, not a hard dependency for the alert itself.

---

## Research / evaluation

### Why CICIDS2017?
Modern labelled flow benchmark (vs outdated KDD-era sets); widely used; MachineLearningCVE export matches our pipeline.

### Dataset limitations?
Lab scenarios, dated relative to today’s traffic, class imbalance, scenario-structured days ≠ continuous enterprise traffic.

### Temporal holdout?
Score **frozen** models on Friday day samples vs IID test — no retrain. Binary stays strong; Friday multiclass only covered Bot/DDoS/PortScan (not full 6-class). Mon–Thu shows mild F1 drop.

### Data drift?
IID train→test: **0** features with PSI ≥ 0.2 — expected under stratified same-corpus split. **Does not** prove live drift absence.

### Residual errors?
Binary FP 1,377 / FN 255 on IID test. Multiclass: 18 confusions / 85k attacks, mainly PortScan/DoS/WebAttack.

### External dataset?
**Not performed** in current scope — stated as **future work** (do not invent results).

### Overfitting?
High IID scores + dual selectors + held-out test + temporal/drift checks; still not a live guarantee. Discuss composition shift (attack rates differ by day).

---

## Architecture / product

### What’s the contribution?
**Integrated decision-support framework**: detect → classify → explain → risk → recommend → simulate — **not** a novel ML algorithm claim.

### Why separate simulation?
Safe pedagogy: show lifecycle without generating attacks or touching production networks.

### Why no automatic firewall blocking?
Ethics + scope: student prototype; destructive automation is out of scope and unsafe to claim.

### How is an incident created?
Prediction/pipeline persists incident with attack type, confidence, risk, recommendation; lifecycle statuses for analyst workflow.

### Risk vs confidence?
Confidence = model certainty. Risk = weighted blend (50% attack base, 25% confidence, 15% intensity, 10% asset criticality).

---

## Security / engineering (honest)

### How is the API protected?
P4 password login + server RBAC and P5 rate limits / request-size limits are in place on `productionization`. Auth remains **off by default** for local demo (`AEGIS_AUTH_ENABLED`); **rate limiting and request-size limits are ON by default** (CI sets `DISABLE_RATE_LIMIT`). Optional API-key path still available via `api.auth.enabled` / `AEGIS_API_KEY`.

### Input validation?
Feature schema / CSV ingest validation; standardized error envelopes; `/api/ready` when models missing.

### Is this production-ready?
**Foundations yes; full production IDS no.** Missing/partial: live capture, full IAM, real response integrations, full load/DR story. Stage-2 branch adds ingest/queue/hardening scaffolding.

### Docker?
`docker compose` demo path with `DEMO_MODE=true`; production would turn demo off and enable auth/rate limits.

---

## Trap questions — short rebuttals

| Trap | Reply |
|------|--------|
| “So you built a new IDS algorithm?” | “No — integration and evaluation of established models.” |
| “100% multiclass on Friday means perfect?” | “Only three families present in that sample.” |
| “PSI=0 means no drift ever?” | “Only IID train→test; temporal/live differ.” |
| “Can we deploy tomorrow?” | “Research/prototype; productionization is separate.” |
| “Show live packet capture.” | “Out of freeze scope; Stage-2 has offline PCAP/CSV scaffolding.” |

---

## Quick numbers card (memorize)

| Item | Value |
|------|------:|
| Binary model | Decision Tree @ 0.85 |
| Multiclass | Random Forest (6 attack classes) |
| Binary F1 / ROC-AUC | 0.99048 / 0.99916 |
| Multiclass macro-F1 | 0.99813 |
| Risk weights | 50 / 25 / 15 / 10 |
| Features | f_classif, k=40 |
| Calibration | Off |

Demo flow: [`DEMO.md`](DEMO.md)
