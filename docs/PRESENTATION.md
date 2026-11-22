# Aegis IDS — Final Presentation Outline (22 slides)

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
| Research (IID) | Binary F1 **0.99382** @ 0.85 (0.99048 @ 0.5); Bot / WebAttack detected 57 % / 37 % |
| Simulation assumptions | DDoS efficacy **0.82** |
| Controlled-lab (P11) | Harness validation: DDoS `BLOCK_SOURCE` 1.00 by construction |
| Research (open-set) | LOAFO zero-day recall **0.706** vs 0.490 at α = 1 %; R3 gain in 6 of 6 models |

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
- Binary test @ deployed 0.85: F1 **0.99382** · Recall **0.992** · FPR **0.091 %** (historical 0.99048 / 0.997 were @ 0.5)
- PR-AUC **0.99744** · ROC-AUC **0.99916** (threshold-free)
- Multiclass test: macro-F1 **0.99813** · weighted-F1 **0.99979** — *given a perfect stage 1*
- End-to-end @ 0.85: Bot **57.1 %**, WebAttack **37.3 %** detected — the minority-family weakness
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

## Slide 14 — P11 harness validation (deterministic by construction)
| Scenario | Harness value | Sim prior |
|----------|---------:|----------:|
| DDoS `BLOCK_SOURCE` | **1.00** | 0.82 |
| DoS `RATE_LIMIT` | **0.80** | 0.78 |
- CONTROLLED lab only · values hold by construction of the test adapter (not measured mitigation) · priors **not** overwritten

## Slide 15 — P12 security validation
- Ten categories · **Overall: PASS**
- Frozen artifact hashes intact · LIVE still forbidden
- Productionized **prototype**, not enterprise SOC claim

## Slide 16 — Research track: Aegis-OSR
- Closed-set classifiers cannot reject unseen families
- Evidence: classifier `1 − P(benign)` + distance to 5 nearest benign flows → benign surprisals → **Fisher sum** → split-conformal p-value
- FPR ≤ α only while traffic is exchangeable · advisory Zero-Day Gate beside the frozen model
- Figure: `docs/research/paper_build/figs/fig2_aegis_osr.png`

## Slide 17 — Research results: where it works and where it breaks
| Setting | Result |
|---|---|
| LOAFO, Aegis-OSR @ α = 1 % | **0.706** [0.689, 0.723], FPR 1.00 % |
| Same XGBoost / decision tree | 0.490 / 0.241 |
| Temporal Mon–Thu → Fri | FPR **7.09 %** |
| CICIDS2017 → CSE-CIC-IDS2018 | FPR **36.7 %** · frozen v1.1 F1 **0.278** |
| 2018 recalibrated per day | FPR 1.62 %, known recall 0.088 · fusion − classifier **−0.237** |
- Recalibration restoring FPR but not detection = prior work (Şahin & Mert 2026), not claimed

## Slide 18 — Pre-registered R3 campaign
- 6 tree models · seeds 101–105 · 4 protocols · 780 records · hypotheses committed before any result
- A4 valid (24/24) · **A1 gain 6/6** (+0.134 to +0.268) · A2 model matters · **A5 2018 loss 6/6** · A6 no transfer · A7 rejected · RS1/RS2 rejected
- Robust to leave-one-family/day-out (A7 → inconclusive); XGBoost gain replicates (+0.218 → +0.228)

## Slide 19 — Negative results, reported
- Phase 7 gate closed by the pre-registered rule → no new method built
- Screen flags 62–100 % of benign warm-up flows on every 2018 day
- Not claimed: universal zero-day detection · guaranteed FPR under shift · transfer
- Exploratory: kNN reference refresh removes most of the 2018 loss → needs its own pre-registered test

## Slide 20 — System demonstration
- Point to live demo flow (`docs/DEMO.md`)
- Detection → incident → propose → dry-run → approve → simulation → System/ops → Research Lab (R3 tab)

## Slide 21 — Limitations & future work
- IID ≠ live traffic · frozen v1.1 F1 0.278 on CSE-CIC-IDS2018
- Zero-day detection measured in distribution, not guaranteed · FPR bound breaks under shift
- R3 scope: six CPU tree models, defaults, 5 seeds · TabM / CLOSR / CatBoost / tuning not run
- P11 ≠ real firewall · simulation ≠ measurement
- Future: pre-registered reference-refresh test · NF-v3 / LycoS confirmation · GPU campaign

## Slide 22 — Conclusion & Q&A
- Defensible claim (one sentence from PRODUCTION_READINESS)
- Tags: `v1.1-research` · `v2.0-aegis-productionized`
- Questions → `docs/VIVA_QA.md` · `docs/PROJECT_REPORT.md`

---

## Timing guide (~13–15 min talk + demo)

| Segment | Slides | Time |
|---------|--------|------|
| Problem → proposal | 1–5 | ~2 min |
| Architecture → ML | 6–10 | ~3 min |
| XAI · sim · response | 11–13 | ~2 min |
| P11 · P12 | 14–15 | ~1.5 min |
| Research track | 16–19 | ~3 min |
| Demo pointer · limits | 20–21 | ~1 min |
| Close | 22 | ~0.5 min |
| Live demo | — | 3–4 min |
