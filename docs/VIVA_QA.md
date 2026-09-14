# Aegis IDS — Comprehensive Viva Q&A Pack

**Tags:** research freeze `v1.1-research` · product `v2.0-aegis-productionized`  
**Source of truth:** [`PROJECT_REPORT.md`](PROJECT_REPORT.md)  
**Demo playbook:** [`DEMO.md`](DEMO.md) · **Slides:** [`PRESENTATION.md`](PRESENTATION.md)

Use **short answers first**; expand only if asked. Never collapse the three measurement classes.

---

## Measurement classes (say this if numbers are challenged)

| Class | Meaning | Memorize examples |
|-------|---------|-------------------|
| **Research (IID / temporal)** | Frozen DT/RF on CICIDS2017 splits | Binary F1 **0.99048** · macro-F1 **0.99813** · Friday F1 **0.99770** |
| **Simulation assumptions** | Visualization priors in `config.yaml` | DDoS **0.82** · DoS **0.78** |
| **Controlled-lab (P11)** | Measured on `TestNetworkAdapter` | DDoS `BLOCK_SOURCE` **1.00** · DoS `RATE_LIMIT` **0.80** |

**P12** is a security-validation outcome (**Overall PASS**), not a detection F1.

---

## Timed project explanations

### 30 seconds

> Aegis IDS is a productionized IDS **prototype**: frozen Decision Tree + Random Forest on CICIDS flow features, SHAP explanations, risk and advisory defenses, then a **human-approved CONTROLLED** response path and attack–defense **simulation**. Research F1 is **0.99048**; simulation priors (**0.82 / 0.78**) are assumptions; P11 lab mitigation is **1.00 / 0.80**; P12 security validation **PASS**. We do **not** auto-block live networks.

### 1 minute

> Traditional demos often stop at “attack detected.” We built an end-to-end decision-support stack: preprocess CICIDS-style flows → binary detection (DT @ **0.85**) → attack-family RF → SHAP → risk → recommendation → incident → propose / dry-run / approve → CONTROLLED lab adapter with verify/rollback → plus pedagogical simulation. The contribution is **integration and honest evaluation**, not a novel IDS algorithm. We freeze `v1.1-research` metrics, productionize through **P0–P12**, and keep research scores, simulation assumptions, and P11 measurements in separate classes so we never overclaim.

### 3 minutes

> **Problem.** SOC workflows need family, explanation, risk, and a safe response path—not only a black-box alert.  
> **Approach.** Two-stage ML on CICIDS2017 (binary then attack-only multiclass), 40 `f_classif` features fit on train only, SHAP primary / LIME secondary, configurable risk blend, advisory recommendations.  
> **Safety.** Response modes are DRY_RUN and CONTROLLED only; LIVE is forbidden; approval is mandatory; reclaim never auto-replays.  
> **Evidence.** IID binary F1 **0.99048**, multiclass macro-F1 **0.99813**; temporal Friday F1 **0.99770** with documented limits; simulation priors **0.82/0.78**; P11 measured **1.00/0.80**; P12 **PASS**.  
> **Limits.** Benchmark ≠ live traffic; no zero-day claim; no external dataset yet; P11 is not a real firewall.  
> **Claim.** Productionized, security-validated **prototype** with a hard boundary against live enforcement.

---

# 1. Project fundamentals

### What problem does Aegis solve?
Many IDS demos stop at classification. Analysts also need **family**, **why**, **how severe**, and **what to do next**—with **human control** over any response.

### What are the objectives?
Detect malicious vs benign; classify six attack families; explain (SHAP/LIME); score risk; recommend advisory defenses; simulate lifecycle; provide CONTROLLED response with approval/verify/rollback; productionize P0–P12 without changing frozen ML artifacts.

### What is the novelty / contribution?
**Not** a novel IDS learning algorithm. Contribution = **reproducible end-to-end decision-support framework** + honest separation of research / simulation / lab measurements + productionization and security validation.

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
Drop Flow ID / IPs / Timestamp / ports (as configured). **StandardScaler + SelectKBest** fit **on train only**. Dual selectors (binary vs multiclass).

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

### Binary test (DT @ 0.85) — research

| Metric | Value |
|--------|------:|
| Precision | 0.98404 |
| Recall | 0.99700 |
| **F1** | **0.99048** |
| PR-AUC | 0.99744 |
| ROC-AUC | 0.99916 |
| FP / FN | 1,377 / 255 |
| TN / TP | 417,635 / 84,884 |
| FPR / FNR | ~0.00329 / ~0.00300 |

### Multiclass test (RF) — research

| Metric | Value |
|--------|------:|
| Accuracy | 0.99979 |
| Macro F1 | **0.99813** |
| Weighted F1 | 0.99979 |
| Macro Precision / Recall | 0.99762 / 0.99864 |

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
> Under the tested controlled environment and scenario, measured outcomes were **1.00** (DDoS block) and **0.80** (DoS rate-limit). Simulation priors **0.82 / 0.78** remain assumptions and were not overwritten.

### What these numbers are **not**?
Not production firewall/EDR effectiveness. Not NIC packet capture. Hard `BLOCK_SOURCE` can yield 1.0 **by construction** of the test gate — validates the measurement framework more than claiming live block rates.

---

# 11. Generalization (P10)

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
**Not performed** — future work. Do not invent CSE-CIC-IDS2018 results.

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
2. No zero-day / unknown-class detection claim  
3. No external-dataset validation yet  
4. Incomplete temporal multiclass (Fri missing BruteForce/DoS/WebAttack)  
5. Simulation efficacy is **assumed**  
6. P11 ≠ real firewall/EDR  
7. No unsupervised live response; LIVE forbidden  
8. PCAP extraction needs optional cicflowmeter (fail closed without it)  
9. Auth may be off in research demos  
10. Not an enterprise SOC (no SLA / HA / full SOAR)

---

# 15. Future work

1. Cross-dataset evaluation under **frozen** preprocessing  
2. Broader temporal multiclass across all six families  
3. Sandbox/opt-in real adapters **only after** CONTROLLED maturity + same approval model  
4. Online drift monitoring beyond IID PSI  
5. Richer case-management UX, advisory-first defaults  
6. Optional novelty/unknown-class as a **separate** experiment (do not retune freeze on that holdout)

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
| “External dataset results?” | “Not in scope — stated future work.” |
| “Overfitting?” | “High IID + train-only selectors + held-out test + temporal/PSI checks; still not a live guarantee.” |
| “What’s your strongest academic claim?” | “Frozen reproducible CICIDS baseline + honest generalization + CONTROLLED empirics beside simulation + P12 PASS prototype boundary.” |

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
| Binary F1 / ROC-AUC | **0.99048** / 0.99916 | Research |
| Multiclass macro-F1 | **0.99813** | Research |
| Friday binary F1 | **0.99770** | Research (temporal) |
| Features | `f_classif` k=40 (dual) | Research config |
| Risk weights | 50 / 25 / 15 / 10 | Product config |
| Sim DDoS / DoS | **0.82 / 0.78** | Simulation assumptions |
| P11 DDoS / DoS | **1.00 / 0.80** | Controlled-lab |
| P12 | **PASS** | Security validation |
| Calibration | Off | Research decision |

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

---

*End of viva pack — aligned to final report on `main` / `v2.0-aegis-productionized`.*
