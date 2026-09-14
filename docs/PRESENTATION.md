# Aegis IDS — Final Presentation Outline (18 slides)

**Source of truth:** `docs/PROJECT_REPORT.md` (aligned to `v2.0-aegis-productionized`).  
**Generate PPTX:**

```bash
python scripts/08_export_presentation_pptx.py
# → docs/Aegis_IDS_Viva_Presentation.pptx
```

**Frozen research baseline (`v1.1-research`):** Binary **Decision Tree** @ **0.85** · Multiclass **Random Forest** (six attack families, no BENIGN).  
**Productionized release:** tag **`v2.0-aegis-productionized`**.

### Three measurement classes (say this once early)

| Class | Example |
|-------|---------|
| Research (IID / temporal) | Binary F1 **0.99048** |
| Simulation assumptions | DDoS efficacy **0.82** |
| Controlled-lab (P11) | DDoS `BLOCK_SOURCE` **1.00** |

---

## Slide 1 — Title
- **Aegis IDS**
- Intelligent ML-Based Intrusion Detection & Attack–Defense Simulation
- `v1.1-research` → `v2.0-aegis-productionized`
- Team · College · Year

## Slide 2 — Problem
- Classic IDS: “Attack detected”
- Analyst still needs: type · why · severity · action · visual understanding
- Gap: detection alone ≠ security decision support

## Slide 3 — Motivation & objectives
- Bridge detection → decision support with human control
- Objectives: detect · classify · explain · risk · recommend · simulate · controlled response · productionize safely

## Slide 4 — Existing system limitations
- High CICIDS accuracy without honest generalization
- Opaque models; advisory actions missing
- Simulation confused with real mitigation
- Weak auth / audit / fail-safe story

## Slide 5 — Proposed Aegis IDS
> Detect → Classify → Explain → Risk → Recommend → Approve → CONTROLLED response → Simulate
- Contribution: **integration + honest evaluation**, not a new algorithm claim
- Hard boundary: **no live firewall/EDR · no unapproved auto-response**

## Slide 6 — Architecture
- React UI ↔ FastAPI ↔ ML + Risk + XAI + Response + Simulation ↔ SQLite
- Adapters: DRY_RUN | CONTROLLED | LIVE (forbidden)
- Diagram: `docs/architecture.png` / README

## Slide 7 — Dataset & preprocessing
- CICIDS2017 MachineLearningCVE · ~2.52M flows after cleaning
- Stratified 70/10/20 · `random_state=42`
- StandardScaler + SelectKBest(**f_classif**, k=40) · dual selectors · train-only fit

## Slide 8 — ML architecture
- Stage 1: Benign vs Attack → **Decision Tree** (threshold **0.85**)
- Stage 2: Attack-only → **Random Forest**
- Families: Bot · BruteForce · DDoS · DoS · PortScan · WebAttack

## Slide 9 — Model results (research IID)
- Binary test: F1 **0.99048** · Recall **0.997** · PR-AUC **0.99744** · ROC-AUC **0.99916**
- Multiclass test: macro-F1 **0.99813** · weighted-F1 **0.99979**
- Message: **IID benchmark ≠ live guarantee**
- Figures: confusion + ROC

## Slide 10 — Why Decision Tree?
- Multi-objective weights: recall 0.30 · F1 0.25 · PR-AUC 0.20 · FPR 0.15 · latency 0.10
- XGBoost can win raw F1; DT wins **recall** → selected
- Show `model_binary_f1_vs_recall.png`

## Slide 11 — XAI + Risk
- SHAP primary · LIME secondary (decision support, not causality)
- Risk: 50% attack · 25% confidence · 15% intensity · 10% asset
- Recommendations are **advisory** until human approval

## Slide 12 — Attack–defense simulation
- `idle → … → detected → recommended → defended → recovered`
- Efficacy values in config are **simulation assumptions** (e.g. DDoS **0.82**, DoS **0.78**)
- Visualization only — not measured mitigation

## Slide 13 — Controlled response architecture
- `propose → dry-run → approve → execute → verify → rollback`
- DRY_RUN / CONTROLLED / LIVE(forbidden)
- RBAC: viewer · analyst (propose) · responder/admin (approve)

## Slide 14 — P11 empirical mitigation
| Scenario | Measured | Sim prior |
|----------|---------:|----------:|
| DDoS `BLOCK_SOURCE` | **1.00** | 0.82 |
| DoS `RATE_LIMIT` | **0.80** | 0.78 |
- CONTROLLED lab only · recommendation-only ≠ mitigation · priors **not** overwritten

## Slide 15 — P12 security validation
- Ten categories · **Overall: PASS**
- Frozen artifact hashes intact · LIVE still forbidden
- Productionized **prototype**, not enterprise SOC claim

## Slide 16 — System demonstration
- Point to live demo flow (`docs/DEMO.md`)
- Detection → incident → propose → dry-run → approve → simulation → System/ops

## Slide 17 — Limitations & future work
- No zero-day claim · no external dataset yet · temporal multiclass incomplete
- P11 ≠ real firewall · simulation ≠ measurement
- Future: cross-dataset under frozen preprocess · broader temporal families · opt-in sandbox enforcement later

## Slide 18 — Conclusion & Q&A
- Defensible claim (one sentence from PRODUCTION_READINESS)
- Tags: `v1.1-research` · `v2.0-aegis-productionized`
- Questions → `docs/VIVA_QA.md` · `docs/PROJECT_REPORT.md`

---

## Timing guide (~10–12 min talk + demo)

| Segment | Slides | Time |
|---------|--------|------|
| Problem → proposal | 1–5 | ~2 min |
| Architecture → ML | 6–10 | ~3 min |
| XAI · sim · response | 11–13 | ~2 min |
| P11 · P12 · limits | 14–17 | ~2.5 min |
| Close | 18 | ~0.5 min |
| Live demo | — | 3–4 min |
