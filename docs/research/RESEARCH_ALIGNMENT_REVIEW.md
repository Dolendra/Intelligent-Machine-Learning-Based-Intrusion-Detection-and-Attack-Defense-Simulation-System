# Research alignment review

**Date:** 2026-11-18 (Phase 0). **Basis:** the four Phase 0 reviews (see FULL_REPOSITORY_AUDIT.md), the committed research artifacts and the R2 literature documents. No new experiments were run. Every statement below is labelled as one of:

* **established:** supported by committed artifacts, with the audit ID given;
* **assessment:** the auditor's judgement;
* **open:** not yet known.

---

## 1. Is Aegis genuinely an integrated IDS research framework?

**Assessment: partly.** It is an integrated IDS **application** with a research **track** attached. It is not yet a modular research **framework**.

| Aspect | Status | Evidence |
|---|---|---|
| End-to-end pipeline: flow → detection → open-set gate → explanation → risk → recommendation → approval-gated response → range | IMPLEMENTED, but the flows have defects | ARCHITECTURE_AUDIT §2 (ARCH-2, ARCH-4, ARCH-5); ML_PIPELINE_AUDIT Part A |
| Interchangeable detection models | PARTIALLY IMPLEMENTED (research side only) | `research/r3_models.py` registry and the `AegisOSR(clf_factory=…)` hook exist. The served app hard-codes the v1.1 DT/RF pair and a single gate. |
| Interchangeable open-set methods (Aegis-OSR, CLOSR, …) | PROPOSED | CLOSR exists only as an out-of-tree pilot. No adapter interface exists. |
| Evidence-reliability / drift layer | PROPOSED | `/api/drift` serves a static report. No runtime reliability estimation exists. |
| Common evaluation harness across methods | PARTIALLY IMPLEMENTED | `research/protocols.py` and `scripts/67_r3_run.py`, with leakage checks and score dumps. Tuning and the temporal protocol are missing (RES-10). |
| Clear separation of simulated / emulated / real outcomes | IMPLEMENTED in code; **mislabelled in some docs** | No real enforcement exists (correct). P11 "measured" numbers hold by construction (ML-12). |

The roadmap's "modular research platform" is the target architecture. Treat it as Phase 8 work. Starting it before the research question is settled would be premature.

## 2. Is the open-set contribution distinguishable from existing methods?

**Established (R2 documents):** the following are already published.

| Topic | Published work |
|---|---|
| Conformal FPR control for NIDS | ConFID; the O-RAN workshop paper; HADAR-UAV |
| Conformal collapse and failed adaptation on CIC-IDS2017↔2018 | Frontiers in AI 2026 |
| Conformal evidence combination | MaSF |
| Threshold-free zero-day open-set detection | CLOSR (TNSM 2026) |

Several closest papers remain unread: the Springer 2026 Mondrian triage paper, MDPI Network 6(2):23 on fixed-FPR fusion, and items F4 and F6.

**Assessment:**
* The Aegis-OSR *method* (supervised + kNN surprisals, Fisher fusion, split conformal, Mondrian attribution) is a sound **engineering combination** of known parts. It is **not** a distinguishable methodological contribution, and the documents already say so.
* What *is* distinguishable today is an **empirical finding**: fixed evidence fusion helps in-distribution (LOAFO +0.216 zero-day recall, 5/5 seeds) but becomes harmful under cross-network shift even after FPR recalibration (−0.237 known recall, 5/5 seeds).
* That finding is narrower than currently written:
  * the temporal evidence is neutral at matched FPR (RES-4);
  * the per-day effect comes from 4 of 8 days (RES-7);
  * the mechanism is the classical Fisher-vs-min-p power trade-off (RES-16), so it should be cited, not claimed.

## 3. What weaknesses remain in the methodology?

Ordered by consequence. Full detail is in ML_PIPELINE_AUDIT.md Part B.

1. **Claims exceed the evidence in public documents.**
   * Unconditional "guaranteed FPR" and "recalibration restores control" (RES-1).
   * The paper omits the fusion inversion and generalises from 2 selected days (RES-3).
   * "Inversion specific to cross-network" (RES-4).
   * "Evidence points to an extractor confound" (RES-11).
2. **Design selection reused the reported unknown flows.** For three of the six families, every seed, including the planned R3 seeds, evaluates on the same unknown flows used to choose the fusion rule (RES-6).
3. **Uncertainty is understated.** CIs cover seed variance only, not family or day variance (RES-7). Calibration-conditional FPR at small windows is noisy (RES-5).
4. **Comparisons at unequal realised FPR.**
   * Conformal ties make tree models over-conservative (RES-2).
   * recal+ref couples reference and calibration (RES-8).
   * The per-day protocol has no oracle control (RES-9).
5. **R3 is not ready to run as approved.**
   * Tuning is unimplemented (RES-10).
   * Tie handling will trip H4 (RES-2).
   * There are data-volume and naming asymmetries (RES-18).
6. **Possible shortcut features.** Destination Port is kept in both the production and research pipelines (ML-10, RES-12).
7. **Uncontrolled confounds in 2018:**
   * extractor version;
   * benign composition;
   * label noise (RES-15);
   * tool novelty inside "known" families (RES-13);
   * day × family;
   * file-order "time" (RES-14).
8. **Production-side evaluation claims (main branch):**
   * binary metrics labelled @0.85 were computed at 0.5 (ML-1);
   * minority-family collapse at the deployed threshold (ML-2);
   * contaminated temporal holdout (ML-3).

## 4. Are the datasets sufficient for the research claims?

**Assessment: sufficient for the in-distribution LOAFO claim; insufficient for any general claim about network shift.**

* **What the current data supports:**
  * There is one shift pair: CICIDS2017 → CSE-CIC-IDS2018. It confounds extractor, network, year, tooling and label quality.
  * The only 2018 "unknown" family is Infiltration, which is label-noisy. 2018 therefore offers **no clean zero-day-under-shift test** (RES-13).
  * Minority families are tiny (Bot 1,948; WebAttack 2,143; Heartbleed 11; Infiltration 36), and the same flows recur across seeds.
* **Testable now with existing data:**
  * cross-dataset LOAFO (train on 2017 without family F; test on that family's 2018 days);
  * within-2018 temporal splits;
  * per-day oracle and contamination controls;
  * no-port and extractor-sensitive feature ablations;
  * matched-FPR re-analysis from the existing per-flow dumps (no retraining).
* **Needs new data, which is on HOLD pending permission:**
  * Extractor-vs-network attribution needs a 2×2 design: one extractor across two networks, and two extractors on one network. Candidate sources are LycoS-IDS2017/LycoS-Unicas-IDS2018, NF-v3, or re-extraction of public PCAPs with a single CICFlowMeter build.
  * The LycoS hold and the "no Google Drive copy" rule stand.

## 5. Is the evidence-stream reliability approach defensible?

**Assessment: defensible as a research question, weak as currently formulated.**

* **Defensible:**
  * The heterogeneity is real and large. kNN AUROC ranges from 0.05 to 0.96 across 2018 days.
  * No fixed fusion rule wins in every setting.
  * Recalibration fixes thresholds, not weighting.
* **Weak as formulated (RESEARCH_GAP_ANALYSIS Contribution 1):**
  * **Benign-only reliability signals barely predict stream utility on the discovery data.** kNN benign exceedance vs kNN AUROC over 10 days: Spearman ρ = −0.41, p = 0.24. The pre-registered H1b threshold is ρ ≤ −0.5.
  * **The proposed staleness screen is non-discriminative.** It flags kNN on 10 of 10 days.
  * **H1c can be met trivially by dropping the novelty stream.** The bar must instead be superiority over the best fixed alternative at matched realised FPR, *plus* non-inferiority on unknown-family recall under shift.
* **What would falsify the direction:**

  | ID | Falsifying outcome |
  |---|---|
  | F1 | Benign-only statistics fail to predict stream utility on new targets (\|ρ\| < 0.3). |
  | F2 | Gated fusion fails to beat the best fixed alternative at matched FPR on both known recall and cross-dataset-LOAFO unknown recall. |
  | F3 | Realised FPR exceeds 1.5α on new targets. |
  | F4 | IID LOAFO harm worse than −0.02 (TOST). |
  | F5 | The inversion disappears once the extractor is held fixed. The contribution would then become "extractor robustness", not "network shift". |

* **Consistency with the user's decision F:** "Do not assume gated fusion will work. Establish its support and rejection criteria before evaluating it." The criteria above are proposed for that purpose and need approval.

## 6. What must be fixed before a journal-level submission?

1. **Correct overstated claims:** RES-1, RES-3, RES-4, RES-11, plus the approved sentence replacement (decision E). For `main`-branch documents: ML-1, ML-2, ML-3, ML-12. Documentation only; no result changes.
2. **Report matched-FPR comparisons** everywhere fusion variants are compared. The data already exist in the per-flow dumps.
3. **Fix R3 before any campaign run:**
   * randomised conformal p-values, or matched-FPR reporting (RES-2);
   * implement and freeze tuning (RES-10);
   * add the temporal protocol;
   * equalise data volume or document the difference (RES-18);
   * amend H1/H4.
4. **Confirm on data never used for design:** time-split small families, cross-dataset LOAFO, and an independent dataset once permission exists (RES-6).
5. **Add family- and day-level uncertainty** (RES-7).
6. **Add controls:** no-port ablation (RES-12); per-day oracle and contamination tests (RES-9, RES-15); timestamp-ordered 2018 (RES-14).
7. **Read the remaining closest papers** (Springer Mondrian triage, MDPI fusion, F4, F6) before any novelty statement.
8. **Fix the artifact-guard gaps** (RES-17) so that new runs cannot overwrite protected results.

## 7. What work should stop?

* **Cosmetic UI work and new simulation features.** The UI needs correctness fixes (ARCH-2/4/5/6), not new pages.
* **Treating P11 "measured mitigation" as evidence.** Keep it as a harness test (ML-12).
* **Maintaining four parallel scenario/replay engines** (ARCH-27). Freeze `simulation/` as a legacy demo.
* **Large GPU runs before the protocol fixes.** The previously approved TabM and CLOSR budgets (decision C) would currently produce comparisons at unequal realised FPR and with default hyperparameters (RES-2, RES-10). **Recommendation:** keep the approval but defer execution until those fixes are reviewed. This is the user's decision.
* **Extending recal+ref results** until W_r and W_c are separated in time (RES-8).
* **TabICL and CLOSR beyond 5 seeds:** already deferred; keep them deferred.
* **The `productionization` and `stage2/productionization` branches:** fully merged into `main` (0 commits ahead). No work should target them. Deleting remote branches requires explicit approval and is **not** recommended here.

---

## Verdict: are we aligned with the intended Aegis research goal?

| Dimension | Verdict | Why |
|---|---|---|
| **Architectural** | **Partially aligned** | Coherent layered pipeline with sound safety boundaries (no live enforcement; approval gate). It is not modular at the serving layer, and it has single-process state and deployment defects (ARCH-1, ARCH-3, ARCH-8, ARCH-13). |
| **Technical** | **Not yet** | All tests pass (297 Python on v3, 213 on main, 49 frontend), but they miss user-visible defects: risk is always 0 on the v3 headline feature (ARCH-2), application logging is silenced (ARCH-3), the Docker image cannot start (ARCH-1), and the default CSV upload rejects the project's own dataset (ARCH-4). Security status is in SECURITY_AUDIT.md. |
| **Scientific** | **Partially aligned** | The core LOAFO result is leakage-free and exactly reproducible. Several published statements exceed the evidence (RES-1, RES-3, RES-4; ML-1 to ML-3 on `main`). The genuinely interesting finding (fusion inversion under shift) is real but narrower than claimed. |
| **Methodological** | **Partially aligned** | Strong practice is in place: artifact protection, an exact regression gate, seed-level statistics, generated paper numbers, a claim audit. But R3 is not campaign-ready (RES-2, RES-10), design and evaluation flows overlap (RES-6), and the proposed reliability method fails its own pre-registered criterion on the discovery data. |

**Overall:** the direction is right, and the research process is unusually disciplined for a student project. Aegis is **not research-ready yet**. The blockers are fixable and mostly cheap: documentation corrections, a handful of code defects, and protocol amendments. They should be closed before R3 compute is spent.


---

## Phase 2 update (2026-11-18)

This update draws on `RESEARCH_INTEGRITY_REPORT.md`, `CLAIM_AUDIT.md` §11 and `R2_LITERATURE_VERIFICATION.md`.

### §2, distinguishability: narrowed further

Three published papers now cover ground that this review left open:
* **Şahin & Mert** (*Electronics* 15(18):4084, 2026) report the 2017→2018 result that recalibration keeps the error
  certificate while detection collapses.
* **Arepalli et al.** (*Discover Informatics* 1:33, 2026; formerly "F4") run LOAFO on CIC-IDS2017 with the same kNN
  mean-distance score.
* **Mchina et al.** (*Network* 6(2):23, 2026; formerly "F6") fuse supervised and anomaly scores at a fixed FPR budget, with
  adaptive per-signal weighting.

The Arepalli et al. full-text statements are not yet independently re-read.

What remains distinguishable is narrow:
* the stream-level account of why fixed Fisher fusion falls below its own classifier after benign-only, time-disjoint
  recalibration (the mechanism itself is classical);
* the matched-FPR evidence that the sign of the fusion effect depends on the setting:
  * in-distribution: +0.218;
  * temporal: neutral;
  * cross-network: −0.202.

Neither is a methodological contribution.

### §3, methodology: progress

* Items 1 and 8 (claims exceeding evidence; production-side claims) are **corrected**.
* Item 3 (uncertainty) is partly addressed: family- and day-level hierarchical intervals now exist for the headline
  comparisons.
* Item 4 (unequal realised FPR) is addressed for analysis: matched-FPR comparisons exist. It is not fixed in the protocol
  (PR-01 is still open).
* Items 2, 5, 6 and 7 are unchanged.

### §5, reliability approach: weaker than before

Max fusion already recovers almost all of the classifier's post-shift detection at matched FPR (−0.043, CI [−0.152, +0.033]).
A reliability-gated method must therefore beat max fusion and supervised-only, not Fisher. The pre-registered H1b already
fails on the discovery data.

### Updated verdict

| Dimension | Verdict |
|---|---|
| Scientific | **Claims now match the evidence** in the corrected documents. The R1b LaTeX recompile is pending. |
| Methodological | **Partially aligned.** R3 is not ready (PR-01 to PR-04 open; H1c bar must change). |
