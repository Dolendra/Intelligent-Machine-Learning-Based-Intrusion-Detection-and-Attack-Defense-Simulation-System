# Aegis IDS — Comprehensive Viva Q&A Pack

**Tags:** research freeze `v1.1-research` · product `v2.0-aegis-productionized` · open-set research track and R3 campaign on `main` (section 11A)  
**Source of truth:** [`PROJECT_REPORT.md`](PROJECT_REPORT.md)  
**Demo playbook:** [`DEMO.md`](DEMO.md) · **Slides:** [`PRESENTATION.md`](PRESENTATION.md)

Use **short answers first**; expand only if asked. Never collapse the three measurement classes.

---

> **Phase 2 corrections (2026-11-18) — read before memorising numbers.**
> * Binary F1 0.99048 / recall 0.99700 are **@ 0.5 (argmax)**, not @ 0.85. At the deployed 0.85: F1 **0.99382**, recall **0.99217**,
>   FPR **0.091 %** (`research_artifacts/v11_reeval/v11_test_metrics_by_threshold.json`).
> * Macro-F1 0.99813 assumes a perfect first stage. At 0.85 the system detects **57.1 % of Bot** and **37.3 % of WebAttack** flows.
> * Friday F1 0.99770 is **superseded (contaminated)**: about 70 % of those rows were training rows. Do not quote it.
> * P11 1.00 / 0.80 are **harness validation, deterministic by construction**, not measured mitigation.
> * Destination Port **is** a model feature.

## Measurement classes (say this if numbers are challenged)

| Class | Meaning | Memorize examples |
|-------|---------|-------------------|
| **Research (IID)** | Frozen DT/RF on the CICIDS2017 random test split | Binary F1 **0.99382** @ 0.85 (0.99048 @ 0.5) · stage-2 macro-F1 **0.99813** (perfect stage 1 assumed) · Bot / WebAttack detected 57.1 % / 37.3 % @ 0.85 |
| **Simulation assumptions** | Visualization priors in `config.yaml` | DDoS **0.82** · DoS **0.78** |
| **Controlled-lab (P11)** | Harness validation on `TestNetworkAdapter`, deterministic by construction | DDoS `BLOCK_SOURCE` 1.00 · DoS `RATE_LIMIT` 0.80 (by construction; not mitigation measurements) |
| **Research (open-set)** | Aegis-OSR and the pre-registered R3 campaign: unseen-family and cross-network detection at a fixed false-alarm rate | LOAFO zero-day recall **0.706** vs **0.490** (same classifier alone) at α = 1 % · fusion gain in **6 of 6** models · frozen v1.1 F1 on CSE-CIC-IDS2018 **0.278** |

**P12** is a security-validation outcome (**Overall PASS**), not a detection F1.

---

## Timed project explanations

### 30 seconds

> Aegis IDS is a productionized IDS **prototype**: frozen Decision Tree + Random Forest on CICIDS flow features, SHAP explanations, risk and advisory defenses, then a **human-approved CONTROLLED** response path and attack–defense **simulation**. Research F1 is **0.99382** at the deployed 0.85 threshold (0.99048 at 0.5), but Bot and WebAttack detection at 0.85 is only 57 % / 37 %; simulation priors (**0.82 / 0.78**) are assumptions; P11 1.00 / 0.80 validates the lab harness (by construction); P12 security validation **PASS**. We do **not** auto-block live networks. Our research track adds a conformal zero-day gate: in distribution it raises unseen-family detection from 0.49 to 0.71 at a 1 % false-alarm rate, but a pre-registered campaign shows the same fusion loses detection on a new network.

### 1 minute

> Traditional demos often stop at “attack detected.” We built an end-to-end decision-support stack: preprocess CICIDS-style flows → binary detection (DT @ **0.85**) → attack-family RF → SHAP → risk → recommendation → incident → propose / dry-run / approve → CONTROLLED lab adapter with verify/rollback → plus pedagogical simulation. The contribution is **integration and honest evaluation**, not a novel IDS algorithm. We freeze `v1.1-research` metrics, productionize through **P0–P12**, and keep research scores, simulation assumptions, and P11 measurements in separate classes so we never overclaim.

### 3 minutes

> **Problem.** SOC workflows need family, explanation, risk, and a safe response path—not only a black-box alert.  
> **Approach.** Two-stage ML on CICIDS2017 (binary then attack-only multiclass), 40 `f_classif` features fit on train only, SHAP primary / LIME secondary, configurable risk blend, advisory recommendations.  
> **Safety.** Response modes are DRY_RUN and CONTROLLED only; LIVE is forbidden; approval is mandatory; reclaim never auto-replays.  
> **Evidence.** IID binary F1 **0.99382** @ 0.85 (0.99048 @ 0.5); stage-2 macro-F1 **0.99813** given a perfect stage 1; Bot / WebAttack detected 57.1 % / 37.3 % @ 0.85; the P10 Friday result is superseded (contaminated); simulation priors **0.82/0.78**; P11 harness validation **1.00/0.80** (by construction); P12 **PASS**.  
> **Research.** Aegis-OSR fuses the classifier with a kNN benign-novelty score and calibrates it conformally. Unseen-family recall **0.706** vs **0.490** at α = 1 %; the gain holds for all six tree models in a pre-registered campaign, but after cross-network recalibration fusion detects *fewer* known attacks for all six, and our proposed reliability screen was rejected.  
> **Limits.** Benchmark ≠ live traffic; zero-day detection measured, not guaranteed; the false-alarm bound breaks under shift; P11 is not a real firewall.  
> **Claim.** Productionized, security-validated **prototype** with a hard boundary against live enforcement.

---

# 1. Project fundamentals

### What problem does Aegis solve?
Many IDS demos stop at classification. Analysts also need **family**, **why**, **how severe**, and **what to do next**—with **human control** over any response.

### What are the objectives?
Detect malicious vs benign; classify six attack families; explain (SHAP/LIME); score risk; recommend advisory defenses; simulate lifecycle; provide CONTROLLED response with approval/verify/rollback; productionize P0–P12 without changing frozen ML artifacts.

### What is the novelty / contribution?
**Not** a novel IDS learning algorithm. Contribution = **reproducible end-to-end decision-support framework** + honest separation of research / simulation / lab measurements + productionization and security validation. On the research side: a **pre-registered measurement** of when fusing supervised and novelty evidence helps (in distribution, all six models) and when it hurts (after cross-network recalibration). That recalibration restores the false-alarm rate but not detection is prior work (Şahin & Mert, 2026); we do not claim it.

### One-line architecture?
`Flow → preprocess → binary ML → family → risk → XAI → recommendation → incident → propose/dry-run/approve → CONTROLLED response → verify/rollback → simulation → SOC UI`

### Stack?
Python · scikit-learn / XGBoost (compared) · SHAP/LIME · FastAPI · React · SQLite.

### Tags / provenance?
`v1.1-research` = frozen academic models + IID metrics. `v2.0-aegis-productionized` = P0–P12 on `main`.

---

# 2. Dataset

### Why CICIDS2017?
Modern labelled flow benchmark (Sharafaldin et al., 2018); widely used; MachineLearningCVE CSVs match our pipeline better than dated KDD-era sets.

### Scale and cleaning?
~2.83M raw rows → rare classes (&lt;50 samples, e.g. Infiltration/Heartbleed) dropped → ~**2.52M** usable. Labels normalized (e.g. DoS Hulk → DoS).

### Split?
Stratified **70 / 10 / 20** train / val / test · `random_state=42` · `sample_frac=1.0`  
Train **1,764,525** · Val **252,075** · Test **504,151**.

### Imbalance?
Attacks are minority (~16.9% on IID test). Prefer **F1 / PR-AUC / recall**, not accuracy alone.

### Leakage control?
Drop Flow ID / IPs / Timestamp where present. **Destination Port is kept as a feature** (possible shortcut, ML-10). **StandardScaler + SelectKBest** fit **on train only**. Dual selectors (binary vs multiclass).

### Raw data in Git?
**No** (size/licensing). Demo uses bundled `models/trained_models/demo_flows.json` — **no raw CICIDS required** for viva demo.

### Dataset limitations?
Lab scenarios; dated vs today’s traffic; day-structured attacks ≠ continuous enterprise traffic; composition shifts by day.

---

# 3. Machine learning

### Why two-stage?
Stage-1: **BENIGN vs ATTACK** (alert). Stage-2: family **without BENIGN** (triage). Cleaner operationally than one flat multiclass including benign.

### Binary model?
Frozen **Decision Tree**, threshold **0.85**.

### Multiclass model?
Frozen **Random Forest**, attack-only: Bot, BruteForce, DDoS, DoS, PortScan, WebAttack.

### Why DT not XGBoost for binary?
Multi-objective val score: recall **0.30**, F1 **0.25**, PR-AUC **0.20**, FPR **0.15**, latency **0.10**. XGB can win raw F1; DT won on **IDS-oriented recall** (selection score **0.9940** vs XGB **0.9918**).

### Why RF for multiclass?
Selection ≈ `0.7·macro-F1 + 0.3·weighted-F1`; RF edged XGB on freeze validation.

### Why 40 features / `f_classif`?
`SelectKBest(f_classif, k=40)` — dual selectors on train only. Reduces dimensionality; limits leakage. Not mutual-info in the freeze.

### Why threshold 0.85?
From threshold operating-point research; balances precision/recall for the freeze. Certainty band **[0.10, 0.95]** is separate from the decision threshold.

### Calibration?
Disabled. Sample isotonic helped ECE slightly but hurt Brier/recall → `use_calibrated_binary: false`.

### Did P0–P12 change models?
**No.** Frozen joblibs and published IID metrics are immutable.

---

# 4. Evaluation (research metrics)

### Binary test (DT) — research, both operating points

The historical table was headed "DT @ 0.85" but was computed at argmax 0.5 (ML-1).

| Metric | @ 0.5 (historical) | @ 0.85 (deployed) |
|--------|------:|------:|
| Precision | 0.98404 | 0.99549 |
| Recall | 0.99700 | 0.99217 |
| **F1** | **0.99048** | **0.99382** |
| PR-AUC / ROC-AUC | 0.99744 / 0.99916 | same (threshold-free) |
| FP / FN | 1,377 / 255 | 383 / 667 |
| FPR | 0.00329 | 0.00091 |

Per family at 0.85 (end-to-end): Bot 57.1 % (n = 389), WebAttack 37.3 % detected (n = 429); all other families ≥ 99.4 %.
Source: `research_artifacts/v11_reeval/`.

### Multiclass test (RF) — research

| Metric | Value |
|--------|------:|
| Accuracy | 0.99979 |
| Macro F1 | **0.99813** |
| Weighted F1 | 0.99979 |
| Macro Precision / Recall | 0.99762 / 0.99864 |

These multiclass figures assume a **perfect first stage**. End-to-end 7-class macro-F1 at 0.85 is **0.881**.

### What does F1 mean here?
Harmonic mean of precision and recall — appropriate under class imbalance when both false alarms and misses matter.

### What does PR-AUC emphasize?
Precision–recall tradeoff under imbalance (often more informative than ROC alone for rare attacks).

### Residual errors?
Multiclass: **18** confusions / ~85k attacks; mainly PortScan / DoS / WebAttack (`ERROR_ANALYSIS.md`).

### Do these guarantee live performance?
**No.** Strong **in-dataset** discrimination only. See generalization + limitations.

---

# 5. XAI

### Why SHAP?
Primary **local** feature attributions for analyst trust and triage. Decision support — **not** causal proof.

### Why LIME?
Secondary local linear surrogate for complementary intuition.

### If SHAP fails?
Surface fallback/error; alert still stands. Explanation is not a hard dependency for detection.

### Counterfactuals?
Optional “what-if” for analyst exploration — illustrative, not ground truth.

---

# 6. Risk engine

### Formula (config blend)?
`0.50·attack_base + 0.25·confidence·100 + 0.15·intensity·100 + 0.10·asset_criticality`

### Risk vs confidence?
**Confidence** = model certainty. **Risk** = weighted operational severity for triage.

### Severity bands?
Low / Medium / High / Critical (project convention).

### Recommendations?
Mapped from family + severity to **advisory** actions (monitor, rate-limit, block source, isolate, escalate). Do **not** auto-change a live network.

---

# 7. Simulation

### What is it?
Safe **visualization** of attack–defense lifecycle on a simplified topology — pedagogy/demo, not measured mitigation.

### State machine?
`idle → normal → attack_start → attack_impact → detected → recommended → defended → recovered`

### Simulation assumptions (not measurements)

| Family | Assumed efficacy |
|--------|-----------------:|
| DDoS | **0.82** |
| DoS | **0.78** |
| PortScan | 0.85 |
| BruteForce | 0.88 |
| WebAttack | 0.90 |
| Bot | 0.92 |

### Simulation vs P11?
Simulation priors stay labelled assumptions and were **not** overwritten by P11. Cite them **side by side**.

---

# 8. Productionization P0–P12

| Phase | Solved |
|-------|--------|
| **P0** | Freeze research baseline (`v1.1-research`); immutable joblibs |
| **P1** | PCAP/CSV ingest validation, queue, safe reject |
| **P2** | Response propose / dry-run / approve gate |
| **P3** | CONTROLLED `TestNetworkAdapter`; LIVE forbidden |
| **P4** | Auth + server-enforced RBAC |
| **P5** | Rate limits, size caps, CORS, headers, WS auth |
| **P6** | Durable persistence (users/actions/audit; Alembic) |
| **P7** | Observability, metrics, `/api/ready`, System UI |
| **P8** | Performance envelope measured; ML not primary bottleneck |
| **P9** | Failure recovery / DR; reclaim without auto-replay |
| **P10** | Generalization honesty (temporal + PSI) |
| **P11** | Empirical CONTROLLED-lab mitigation measurements |
| **P12** | Final security validation → **Overall PASS** |

Post-merge verification: `docs/POST_MERGE_VERIFICATION.md` (**PASS**).

---

# 9. Security & controlled response

### Modes?

| Mode | Behavior |
|------|----------|
| `DRY_RUN` | Preview only; no live change |
| `CONTROLLED` | In-memory `TestNetworkAdapter` only |
| `LIVE` | **Forbidden** |

### Lifecycle?
`propose → dry-run → approve → execute → verify` · reject path · verify fail → **rollback** · expire/reclaim → safe **FAILED** (**no auto-replay**)

### RBAC (auth on)?

| Role | Propose / dry-run | Approve / rollback |
|------|-------------------|--------------------|
| viewer | no | no |
| analyst | yes | no |
| responder | yes | yes |
| admin | yes | yes |

Role is **server-bound**; clients cannot escalate via forged actor fields.

### Auth on viva demo?
Usually **off** for open demo (`AEGIS_AUTH_ENABLED` unset). Rate limits / request-size limits are ON by default in hardened configs; CI may disable rate limit for tests.

### Do you block attacks automatically?
**No.** Advisory until Approve; execution only on CONTROLLED lab plane.

---

# 10. P11 empirical mitigation

### What was measured?
Under CONTROLLED synthetic traffic, with approve → `TestNetworkAdapter` → traffic gate, **N=10** reps:

| Scenario | Measured effectiveness | Simulation prior | Δ |
|----------|----------------------:|-----------------:|--:|
| DDoS `BLOCK_SOURCE` | **1.00 ± 0** | 0.82 | +0.18 |
| DoS `RATE_LIMIT` | **0.80 ± 0** | 0.78 | +0.02 |

No-defense / recommendation-only blocked rates were **0.00** in the tested gate.

### Exact citation wording?
> **Corrected (ML-12):** the values **1.00** (DDoS block) and **0.80** (DoS rate-limit) hold by construction of the test adapter; they validate the harness, not mitigation. Simulation priors **0.82 / 0.78** remain assumptions and were not overwritten.

### What these numbers are **not**?
Not production firewall/EDR effectiveness. Not NIC packet capture. Hard `BLOCK_SOURCE` can yield 1.0 **by construction** of the test gate — validates the measurement framework more than claiming live block rates.

---

# 11. Generalization (P10) — SUPERSEDED

> **The Friday result below is contaminated** (about 70 % of the scored rows were training rows; ML-3). If asked about temporal
> generalization, cite the research track's day-ordered Mon–Thu→Fri protocol in `docs/research/RESULTS.md` instead.

### IID vs temporal (binary F1, frozen models)

| Slice | F1 | Notes |
|-------|---:|-------|
| IID test | **0.99048** | Official stratified score |
| Friday sample | **0.99770** | Δ (IID−Fri) = **−0.00722**; attack rate ~34% |
| Mon–Thu sample | **0.97997** | Δ = **+0.01051** (degradation) |

### Friday multiclass trap?
Perfect subset scores cover only **Bot / DDoS / PortScan** present in that sample — **not** six-class temporal proof.

### PSI?
- IID train→test: **0** features with PSI ≥ 0.2  
- Temporal: max PSI **0.2354** (2 features ≥ 0.2)  
Wording: *no feature exceeded PSI threshold in the IID comparison* — **not** “there is no drift.”

### External dataset?
**Performed in the research track** (section 11A). The frozen v1.1 binary model scores F1 **0.278** on CSE-CIC-IDS2018 (precision 0.988, recall 0.162) versus 0.990 IID (`research_artifacts/frozen_v11_on_cic2018_v2.json`). The models were not retrained on 2018.

---

# 11A. Open-set zero-day research (Aegis-OSR and R3)

> Source: `PROJECT_REPORT.md` Chapter 13, `docs/research/R3_RESULTS.md`, `docs/research/EVIDENCE_RELIABILITY_STUDY.md`.

### What is Aegis-OSR, in one breath?
Two evidence scores per flow: the classifier's `1 − P(benign)` and the distance to the 5 nearest **benign** training flows. Each becomes a benign tail probability; they are **added** (Fisher fusion); the sum becomes a **split-conformal p-value**; alert when `p ≤ α`.

### Why conformal?
It gives a finite-sample bound: benign false-alarm rate ≤ α, **if** test benign traffic is exchangeable with the calibration traffic. That "if" is exactly what breaks under drift, and we measure that.

### How do you test zero-day detection honestly?
**LOAFO** (leave one attack family out): remove a family from training entirely, then treat it as the unseen attack. Six families × five seeds; the seed is the statistical unit.

### Headline result?
Unseen-family recall **0.706** [0.689, 0.723] at α = 1 % with realised FPR 1.00 %, versus **0.490** for the same XGBoost alone and **0.241** for a v1.1-style decision tree. Gain **+0.216** [+0.180, +0.252], positive on 5 of 5 seeds.

### Does the false-alarm guarantee hold under shift?
**No.** Mon–Thu → Friday: realised FPR **7.09 %** at a 1 % budget. CICIDS2017 → CSE-CIC-IDS2018: **36.7 %**. Recalibrating on 2,000 benign flows per 2018 day brings the mean FPR to 1.62 %, but known-family recall is then only 0.088.

### What is R3?
A **pre-registered** confirmatory campaign: hypotheses and analysis rules written and committed **before** any result existed, approved, then run. Six tree models (XGBoost ×2, decision tree, random forest, extra trees, LightGBM), new seeds 101–105, four protocols, 780 records. Paired *t*-test with Holm correction; hierarchical bootstrap intervals.

### R3 verdicts?
| ID | Result |
|---|---|
| A4 validity | FPR 0.99–1.06 % in all 24 cells: **supported** |
| A1 LOAFO gain | **6 of 6** models, +0.134 to +0.268: **supported** |
| A2 model matters | Decision tree −0.173 vs XGBoost: **supported** |
| A5 2018 loss after recalibration | Same sign for **6 of 6**: **supported** |
| A6 gain transfers to 2018 unseen families | **No** (setting- and model-dependent) |
| A7 max fusion safe | 0 of 6: **rejected** |
| RS1 / RS2 benign-only reliability screen | ρ = −0.16 / +0.20: **both rejected** |

### Why did you not build the new method (Phase 7)?
The pre-registered rule said: build a gated method only if **both** RS1 and RS2 are supported. Both were rejected: the screen flags 62–100 % of benign warm-up flows on every 2018 day, so it cannot separate good days from bad ones. Building it anyway would have been choosing the method after seeing the data.

### Isn't a negative result a failure?
No. The question was *when* fusion helps or hurts. "It does not transfer, and this screen cannot predict it" is an answer, and reporting it prevents others from deploying a rule that fails under shift.

### Is the result robust?
Leave-one-family/day-out keeps A1, A5 and A6 (A7 becomes inconclusive without one day). The XGBoost gain replicates on new seeds (+0.218 → +0.228). Matched-FPR and conformal recall agree in sign for 6 of 6 models.

### What would you do next?
Pre-register a test of the **reference-refresh** lead (adding warm-up benign flows to the kNN reference removed most of the 2018 loss, exploratory only), then confirm on independent data (NF-v3, LycoS once licensing allows).

### Does the gate change what the live system does?
No. It is **advisory**: the frozen v1.1 detector stays the decision authority (`incident_policy: frozen`). On 82,111 held-out flows the benign incident rate is 0.077 % (frozen), 0.896 % (gate), 0.934 % (union).

---

# 12. Performance (P8)

**Host-specific** (dev Windows envelope; re-measure before citing elsewhere). Flags: `prototype_only`, `not_a_capacity_claim`.

| Workload | Measured point |
|----------|----------------|
| Single-flow offline predict (no SHAP) | ~**68** flows/s · p50 ~15 ms · p95 ~16 ms · 0% error |
| Pipeline batch 500 | ~**125** flows/s |
| Vectorized ML-only 1k–5k | ~**15k–22k** flows/s |

### Bottleneck?
Gap between pipeline (~10²) and vectorized ML (~10⁴) → cost is largely **per-flow enrichment/persistence**, not frozen DT/RF inference. P8 **records**; it does not rewrite that path.

### Not an SLA?
Correct — measured operating point on one host, not multi-node capacity.

---

# 13. Failure recovery (P9)

### Readiness?
`GET /api/ready` — dependencies include database, models, filesystem, queue, pcap extractor. Demo only when `"status": "ready"`.

### Orphan / stale actions?
Startup reclaim marks stale `EXECUTING` / orphan `APPROVED` as **FAILED** with **`auto_reexecute: false`** — **no auto-replay**.

### Why no auto-replay?
Fail-safe: better a visible failed action than silently re-applying network decisions after crash/restart.

### Backup/restore?
Documented DR path for SQLite persistence (prototype scope — not HA cluster claim).

---

# 14. Limitations (what we do **not** claim)

1. Benchmark ≠ production traffic guarantee  
2. Zero-day detection is measured in distribution (LOAFO), not guaranteed; it does not transfer to unseen families on CSE-CIC-IDS2018  
3. The conformal false-alarm bound holds only under exchangeability; it breaks under drift (7.09 % Friday, 36.7 % on 2018)  
4. Incomplete temporal multiclass (Fri missing BruteForce/DoS/WebAttack)  
5. Simulation efficacy is **assumed**  
6. P11 ≠ real firewall/EDR  
7. No unsupervised live response; LIVE forbidden  
8. PCAP extraction needs optional cicflowmeter (fail closed without it)  
9. Auth may be off in research demos  
10. Not an enterprise SOC (no SLA / HA / full SOAR)  
11. R3 scope: six CPU tree models, library defaults, five seeds; TabM, CLOSR, CatBoost, tuning and independent confirmation data not run

---

# 15. Future work

1. Pre-registered test of the reference-refresh lead, then independent confirmation data (NF-v3, LycoS)  
2. Broader temporal multiclass across all six families  
3. Sandbox/opt-in real adapters **only after** CONTROLLED maturity + same approval model  
4. Online drift monitoring beyond IID PSI  
5. Richer case-management UX, advisory-first defaults  
6. A label-free signal for choosing fusion vs the classifier under shift (the benign-only screen failed)  
7. GPU campaign (TabM, CLOSR) and equal-budget tuning

---

# 16. Difficult examiner questions

| Question | Concise defensible answer |
|----------|---------------------------|
| “So you invented a new IDS algorithm?” | “No — integration, evaluation, and productionized decision-support around established models.” |
| “F1 0.99 means you’re production-ready?” | “Strong CICIDS IID result only. Productionization ≠ live accuracy guarantee.” |
| “Why is Friday F1 higher than IID?” | “Different attack-rate composition (~34%); Δ reported honestly; not a free lunch.” |
| “100% Friday multiclass?” | “Only three families present in that sample.” |
| “PSI=0 means no drift ever?” | “Only IID train→test; temporal PSI rises; live unknown.” |
| “You measured 82% mitigation?” | “**No** — **0.82** is a **simulation prior**. P11 measured **1.00 / 0.80** on CONTROLLED lab.” |
| “Then why keep 0.82 if you measured 1.00?” | “Different classes of evidence; we refuse to overwrite assumptions with lab numbers.” |
| “P11 1.00 proves firewall block works?” | “Proves CONTROLLED adapter gate behavior under the test protocol — not NIC/firewall production efficacy.” |
| “Can we deploy and auto-block tomorrow?” | “Prototype only; LIVE forbidden; no unsupervised enforcement.” |
| “Show live packet capture.” | “Out of freeze demo path; optional PCAP ingest exists but needs cicflowmeter; viva uses bundled flows.” |
| “Why not deep learning?” | “Tabular flows; trees are strong, fast, explainable; we compared boosting; policy selected DT/RF.” |
| “Is auth disabled a security failure?” | “Demo default; P4/P5/P12 validate the hardened path; enable auth for non-demo.” |
| “What if approve races?” | “Concurrent approve: atomic claim — measured 1 success / 8 racers in P8.” |
| “Did you tune on the temporal holdout?” | “**No.** Frozen models scored as-is.” |
| “External dataset results?” | “CSE-CIC-IDS2018: frozen v1.1 F1 drops to 0.278; Aegis-OSR's FPR reaches 36.7 % before recalibration. We report the failure.” |
| “So you detect zero-days?” | “Unseen families in distribution: 0.706 vs 0.490 at 1 % FPR, all six models. Not universal: it does not transfer to the new network.” |
| “Did you choose the hypotheses after seeing results?” | “No. R3 was pre-registered and committed before any record existed; deviations are dated in the amendment.” |
| “Why only five seeds?” | “Schedule. The paired t-test is primary; we stated in advance that the minimum exact Wilcoxon p at 5 seeds is 0.0625.” |
| “Why no deep model?” (research) | “TabM and CLOSR need a GPU campaign and CLOSR's data is under a licence hold; deferred and stated, not hidden.” |
| “Overfitting?” | “High IID + train-only selectors + held-out test + temporal/PSI checks; still not a live guarantee.” |
| “What’s your strongest academic claim?” | “Frozen reproducible CICIDS baseline + honest generalization + CONTROLLED empirics beside simulation + P12 PASS prototype boundary; and a pre-registered result that fusion helps zero-day detection in distribution for six models but hurts after cross-network recalibration.” |

---

# 17. Cybersecurity basics (if asked)

### What is an IDS?
Monitors for malicious activity and raises alerts. Ours is a **network-flow ML IDS prototype** (offline CICIDS-style features), not a signature appliance.

### Signature vs ML?
Signatures: precise, brittle. ML: feature generalization, needs careful eval, can false-alarm.

### NIDS vs HIDS?
Network vs host. Aegis is **NIDS-style** (flow features).

### Kill chain / simulation?
Simulation mirrors detect→recommend→defend→recover for teaching; not a full MITRE ATT&CK coverage claim.

---

# 18. Quick numbers card (memorize)

| Item | Value | Class |
|------|------:|-------|
| Binary model | DT @ **0.85** | Research config |
| Multiclass | RF (6 families) | Research config |
| Binary F1 / ROC-AUC | **0.99382** @ 0.85 (0.99048 @ 0.5) / 0.99916 | Research |
| Bot / WebAttack detected @ 0.85 | **57.1 % / 37.3 %** | Research (end-to-end) |
| Multiclass macro-F1 | **0.99813** (perfect stage 1 assumed) | Research |
| Friday binary F1 | ~~0.99770~~ superseded (contaminated) | — |
| Features | `f_classif` k=40 (dual) | Research config |
| Risk weights | 50 / 25 / 15 / 10 | Product config |
| Sim DDoS / DoS | **0.82 / 0.78** | Simulation assumptions |
| P11 DDoS / DoS | **1.00 / 0.80** | Controlled-lab |
| P12 | **PASS** | Security validation |
| Calibration | Off | Research decision |
| LOAFO zero-day recall @ α = 1 % | **0.706** (OSR) vs 0.490 (XGB) vs 0.241 (DT) | Research (open-set) |
| R3 fusion gain (LOAFO) | **+0.134 to +0.268**, 6 of 6 models | Research (open-set) |
| R3 2018 loss after recal | **−0.212 to −0.006**, 6 of 6 same sign | Research (open-set) |
| Frozen v1.1 F1 on CSE-CIC-IDS2018 | **0.278** | Research (external) |
| FPR under shift @ 1 % budget | **7.09 %** Friday · **36.7 %** 2018 | Research (open-set) |
| Release validation | **PASS** (4 gates) | Release |

---

# 19. Artifacts to cite if pressed

| Topic | Path |
|-------|------|
| Model freeze | `models/trained_models/model_metadata.json` |
| Training metrics | `training_report.json` |
| Generalization | `generalization_report.json` · `docs/GENERALIZATION.md` |
| Empirical P11 | `empirical_mitigation_report.json` · `docs/EMPIRICAL_MITIGATION.md` |
| Security P12 | `reports/final_security_validation_report.json` |
| Performance | `docs/PERFORMANCE.md` · `results/performance/operating_envelope_latest.json` |
| Security model | `docs/SECURITY_MODEL.md` |
| Open-set method / results | `docs/research/AEGIS_OSR.md` · `docs/research/RESULTS.md` |
| R3 pre-registration / results | `docs/research/R3_AMENDMENT.md` · `docs/research/R3_RESULTS.md` |
| Reliability study | `docs/research/EVIDENCE_RELIABILITY_STUDY.md` |
| Papers | `docs/research/Aegis_OSR_paper_ieee.pdf` · `docs/research/Aegis_Research_Paper.docx` |

---

*End of viva pack — aligned to the final report on `main` (v2.0-aegis-productionized plus the research track and R3).*
