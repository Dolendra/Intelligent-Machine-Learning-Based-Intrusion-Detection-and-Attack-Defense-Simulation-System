# Critical comparison with the closest prior work — CLOSR (Wilkie et al., TNSM 2026) and FIRCE (Barrett et al., 2026)

**Date:** 2026-11-17 · **Branch:** `v3-openset-research` · **Status:** R2 follow-up, done *before* any novelty claim.

**How this was checked.** Both papers were read in full (arXiv HTML), and both official repositories were read file by file. No code was run and no data was downloaded. The decisive claims were then re-checked by hand against the primary sources (the "Verified" column below). Quotes are verbatim; § numbers refer to each paper.

| Claim used below | Source | Verified |
|---|---|---|
| CLOSR "does not calibrate the value of the threshold"; τ "is not calibrated in this work" | arXiv 2601.09902 §III-C, §III-D | yes |
| CLOSR zero-day classes = "Web Attack (SQL Injections) and Heartbleed", only in the test set | §IV-A | yes |
| CLOSR: one dataset (LycoS-IDS2017, 1,789,954 flows), no cross-dataset or temporal evaluation; cross-network generalisation is future work | §IV-A, §VI | yes |
| CLOSR code computes per-class AUROC as `max(roc, 1 - roc)` | `util/metrics.py`, `mean_auroc` | yes |
| FIRCE status: arXiv v1 only (3 May 2026); "accepted by IEEE SmartNets26" appears only in the arXiv comment field | arxiv.org/abs/2605.01962 | yes |
| FIRCE calibrates on the data the model was fit on (`model_.fit(X, y)`, then `StratifiedKFold` folds of the same `X, y`) | `approx_cce.py` (`calibrate`, `_process_fold`); paper Alg. 1 | yes (code) |

---

## 1. CLOSR — J. Wilkie, H. Hindy, C. Michie, C. Tachtatzis, J. Irvine, R. Atkinson, *A Novel Contrastive Loss for Zero-Day Network Intrusion Detection*, IEEE TNSM 23, 2026, doi:10.1109/TNSM.2026.3652529 (arXiv 2601.09902); code: github.com/jackwilkie/CLOSR (Apache-2.0)

**Publication status.** Peer-reviewed journal (IEEE TNSM). Official code is released, with pretrained weights.

### 1.1 Exact problem
The paper solves two tasks:
* **CLAD:** binary benign-vs-attack detection that should generalise to unseen attacks.
* **CLOSR:** open-set recognition — multiclass classification of known classes plus rejection of unknown classes.

"Zero-day" means an attack class that is present only in the test set.

### 1.2 Method and assumptions
**Architecture.** An MLP encoder with one projection head per class onto the unit hypersphere.

**Loss.** A benign-anchored contrastive loss derived from a von Mises–Fisher likelihood ratio (Eq. 7, rescaled cosine distance, margin m = 1). CLOSR sums this loss one-vs-rest over classes (Eqs. 11–12).

**Scores.**
* Prediction is a softmax over centroid similarities (Eq. 14).
* The unknown score is −Σ_c P(c|x)·(h_c(z)·μ_c)², motivated by near-orthogonality of unknown embeddings to every centroid (Eqs. 15–16).

**Assumptions.**
* Benign traffic is one vMF class; known attacks are labelled.
* Unknown embeddings spread uniformly over the hypersphere.
* Train and test come from the same capture (i.i.d.), and there is no benign drift.

### 1.3 Data and protocol
**Data.** LycoS-IDS2017 only: CICIDS2017 re-extracted with a corrected flow tool (Rosay et al.), using 72 features.

**Split and held-out classes.**
* One random stratified 50/50 split with a fixed seed. It is not temporal.
* The zero-day classes are fixed, not rotated: SQL Injection and Heartbleed, i.e. the classes with fewer than 100 flows. They are removed from training.

**Tuning and repeats.**
* Hyperparameters: 200-iteration random search with 5-fold CV on the training data.
* Results are means over 20 training runs, with a Wilcoxon test (p < 0.01).

**Metrics.** Threshold-free only: AUROC, FPR@95 % recall, and "OpenAUC". The code computes OpenAUC as closed-set accuracy × open-set AUROC, which simplifies the pairwise OpenAUC of Wang et al.

### 1.4 Reported results (means; no variance in the main tables)
* **CLAD zero-day AUROC:** 0.9966.
* **CLOSR:** closed-set accuracy 0.9953, open-set AUROC 0.9740, OpenAUC 0.9694.
* **Strongest baselines:** the Siamese baseline has better closed-set F1 and FP rate (Table IV).

### 1.5 Strengths
* Principled loss with a clear probabilistic motivation.
* Uses corrected data — better than our uncorrected MachineLearningCVE export.
* Many baselines (binary and open-set) with a significance test.
* Cheap inference (0.40 ms).
* Code and weights released.

### 1.6 Limitations (critical)
1. **No operating point.** No threshold is set, so there is no false-alarm control. FPR@95 % recall chooses the threshold *on the test attack class*, which is not deployable.
2. **Two fixed, tiny zero-day classes.** Heartbleed has 11 flows in CICIDS2017. AUROC on this few positives has wide uncertainty, which is not reported. There is no leave-one-family-out rotation, so it is unknown whether the result holds for large, behaviourally different families (DoS, PortScan, Bot).
3. **No shift of any kind.** The protocol is a random split of one capture. The paper itself names cross-network generalisation as future work.
4. **Evaluation code chooses the AUROC orientation after seeing test labels** (`max(roc, 1 - roc)`), and several baselines import this helper. Any method scoring worse than chance is reported as better than chance. This inflates weak baselines' AUROC and makes baseline comparisons less reliable. It does not obviously change CLOSR's own number.
5. **Reproduction gaps.**
   * No seeds are set anywhere, and there is no 20-run driver, no tuning code and no Wilcoxon code.
   * The data must be merged by hand.
   * GPU is the default device.
   * `y` is taken from the frame before `dropna()`, which silently assumes there are no NaN rows.

### 1.7 Overlap with Aegis-OSR
**High on the problem; low on the evaluation question.**

Shared:
* Zero-day / open-set NIDS on CICIDS2017-derived flows.
* Benign-anchored representation of normality.
* Known-family attribution with an unknown option (CLOSR's Eq. 17 formulation, never evaluated with a threshold).

Different:
* Aegis sets an operating point with a conformal benign-FPR bound, rotates six held-out families, and measures shift (temporal, cross-network).
* CLOSR has the stronger representation-learning component and the cleaner data.

### 1.8 What CLOSR leaves unresolved
* At what false-alarm rate is CLOSR's zero-day AUROC usable?
* Does it hold for large held-out families?
* Does it survive day-to-day or cross-network shift?

These are exactly the questions Aegis's protocol asks. **We do not know whether CLOSR's evidence would beat ours inside the same calibrated pipeline.** Until R3 runs that comparison, Aegis must not claim better zero-day detection than CLOSR.

### 1.9 Is the Aegis direction distinct?
**Partly.** The *method* is not more novel than CLOSR's: our evidence is an off-the-shelf classifier plus kNN distance. What is distinct is the *evaluation contract*:
* a fixed, calibrated FPR;
* rotated held-out families;
* seed-level statistics;
* measured failure under shift.

A paper whose main claim is "better zero-day detection" would overlap directly with CLOSR and would need a head-to-head comparison. A paper about calibrated operating points and shift does not.

---

## 2. FIRCE — S. Barrett, L. Li, G. Dorai, S. Rajaganapathy, *FIRCE: A Framework for Intrusion Response and Conformal Evaluation*, arXiv 2605.01962 (v1, 3 May 2026); code: github.com/DFAIR-LAB-Augusta/XSecIoT (branch `FIRCE_bkp`)

**Publication status.** Preprint. The arXiv comment says "accepted by IEEE SmartNets26". We found no proceedings record, so cite it as a preprint (accepted, per the authors) until a DOI exists. Code is public, but the branch has moved beyond the paper (adaptive significance, a CADE monitor, multiclass).

### 2.1 Exact problem
Detect concept drift in a **supervised binary** IoT intrusion classifier, and trigger retraining and recalibration cheaply.

### 2.2 Method and assumptions
**Approach.** Transcend-style *conformal evaluation*, not conformal prediction.
* Non-conformity: 1 − P(ŷ). p-values: class-conditional against the calibration scores of the predicted class.
* Rejection: by class-conditional (1−α) quantile thresholds.
* Approx-CCE: one model fit plus fold-wise calibration.
* An adaptive chunking controller sizes the stream chunks.

**Drift handling.** Drift is "detected based on low-confidence outputs", but the rule is not stated in the paper. In the code, any rejected flow flags the whole chunk. On drift, the model is **retrained on labelled buffer data** and recalibrated.

**Assumptions.**
* The task is binary (benign / malicious).
* Labels arrive quickly enough to retrain.
* Centralised training.
* Exchangeability is never stated.

### 2.3 Data and protocol
**Data.**
* DFAIR: the authors' own testbed of ten IoT devices, with SYN, XMAS, UDP and HTTP floods. The "drift" set adds HULK.
* Cross-dataset runs: CICIDS2018 → DFAIR-Drift and UNSW-NB15 → DFAIR-Drift. The repository points to the NetFlow `NF-UNSW-NB15-v3` file.
* Not stated: the dataset versions, days, feature alignment, splits and seeds.

**Unknown families.** These are not evaluated; open-world detection is listed as future work.

### 2.4 Reported results
* Near-ceiling accuracy and F1 for every method; e.g. F1 0.9999 on DFAIR and 0.98–0.99 for the cross-dataset runs.
* Large runtime and calibration-count savings for adaptive chunking.
* Single runs, with no variance.
* No realized FPR, no rejection rates and no drift-detection delay.

### 2.5 Strengths
* Real hardware testbed.
* An engineering focus on cheap recalibration in streams.
* Public code.

### 2.6 Limitations (critical)
1. **The p-values are not valid conformal p-values.** Calibration scores come from the samples the model was trained on (paper Alg. 1; `approx_cce.py`). Training-set non-conformity scores are optimistically small, so test points look strange too often. Validity, and the "formal guarantees" claimed in §II-A, do not follow. This is the decisive technical difference from Aegis, which calibrates on disjoint held-out benign splits.
2. **No significance level reported.** α is not given in the paper, and there is no coverage or FPR analysis.
3. **Drift is weak.** DFAIR-Drift is another HTTP flood, and the scores are near ceiling, so there is little room to show an effect.
4. **Oracle labels for retraining.**
5. **Internal inconsistencies.**
   * The Table III "Adaptive" rows equal the Table II *CCE* rows, not the Approx-CCE rows they are labelled as.
   * A stated tolerance ("within 10⁻³ on F1") is violated on UNSW (gap 0.0028).
   * "Statistically on par" is claimed without a test.

### 2.7 Overlap with Aegis-OSR
**Keyword-level: high** (conformal, IDS, drift, recalibration, CSE-CIC-IDS2018). **Substantive: low.**

| | FIRCE | Aegis-OSR |
|---|---|---|
| Task | Closed-set binary classifier | Open-set: known families + unknown attacks |
| What the conformal step does | Rejects low-confidence predictions as a drift signal | Calibrates one alert threshold with a stated benign FPR bound |
| Validity | Calibrated in-sample (invalid) | Disjoint benign calibration split (valid under exchangeability) |
| Adaptation | Retrains with labels | Recalibrates on confirmed-benign flows only, no retraining |
| Evaluation of the guarantee | None (no FPR vs α) | Realized FPR vs α under IID, temporal and cross-network shift |

### 2.8 What FIRCE leaves unresolved
* A *valid* conformal drift signal for IDS.
* Benign-FPR control.
* Open-set detection.
* Label-light adaptation.
* Whether detection recovers after recalibration.

### 2.9 Is the Aegis direction distinct?
**Yes, on substance**, but the paper must cite FIRCE and state the differences above. "Conformal drift handling for IDS" is no longer an empty niche at the keyword level.

**Caution about our own Contribution 2 (shift-aware FPR control).** Its framing ("detect violation → recalibrate") reads like FIRCE's loop. The distinction must rest on:
* validity — disjoint calibration, benign-only windows;
* a measured violation of the FPR bound;
* measured detection after recalibration.

The *idea* of recalibrating on drift is not the distinction.

---

## 3. What both papers leave open — and what our own data now says about it

Neither paper measures **detection at a fixed, calibrated false-alarm rate after the environment changes**. The question is whether recalibration restores detection or only restores the false-alarm budget. Our per-day CSE-CIC-IDS2018 records already contain that measurement.

**Analysis.** `scripts/64_recalibration_diagnosis.py` → `research_artifacts/recalibration_diagnosis.json`. It is a post-hoc analysis of committed records: **hypothesis-generating, not confirmatory**. Mean over 10 days × 5 seeds, α = 1 %:

| Method | No recalibration: FPR / known recall | recal@2000: FPR / known recall | AUROC benign vs attacks (recal@2000) |
|---|---|---|---|
| Aegis-OSR (Fisher fusion) | 0.419 / 0.767 | 0.016 / **0.088** | 0.768 |
| Aegis-OSR, max fusion | 0.428 / 0.780 | 0.016 / 0.303 | 0.776 |
| Closed-set XGB (same classifier, no novelty) | 0.046 / 0.687 | 0.014 / 0.325 | 0.819 |
| XGB + Energy | 0.043 / 0.672 | 0.014 / 0.433 | 0.860 |
| kNN distance alone | 0.654 / 0.523 | 0.008 / 0.019 | 0.511 |

**Seed-level paired comparison at recal@2000.** Days are averaged within each seed; n = 5 independent seeds. Known recall relative to Aegis-OSR:

| Method | Difference in known recall vs Aegis-OSR | 95 % CI | Seeds better | p |
|---|---|---|---|---|
| Closed-set XGB | +0.237 | [+0.153, +0.322] | 5/5 | 0.0014 |
| XGB + Energy | +0.345 | [+0.243, +0.446] | 5/5 | 0.0007 |
| Max fusion | +0.215 | [+0.134, +0.296] | 5/5 | 0.0018 |

**Why recalibration lowers false alarms without restoring detection.** Four observations follow from the records:

1. **The pre-recalibration "detection" was mostly a collapsed threshold.** Recall 0.767 came with a 41.9 % false-alarm rate. Recalibration moves the threshold back onto target benign traffic, and the recall that remains is what the score's *target-domain ranking* allows.
2. **The supervised evidence still ranks well after the environment change.**
   * On 2018-02-14 (FTP/SSH brute force), a recalibrated closed-set XGB has known recall 0.984 at 0.7 % FPR (AUROC 0.999).
   * On 2018-02-16 (DoS-Hulk), it has 0.920 at 0.9 % FPR (AUROC 1.000).

   So the tools that the *frozen* v1.1 detector misses on 2018 (Hulk 1.1 %, SSH 0.0 %) are **not undetectable**. Their scores have moved, not vanished.
3. **The novelty stream is stale.** It measures distance to the *2017* benign reference.
   * On 2018 its ranking is at or below chance: mean AUROC 0.51, and 0.05 on 2018-02-16, where attacks sit *closer* to the 2017 benign reference than 2018 benign does.
   * Recalibration cannot repair a ranking, only a threshold.
   * The Fisher sum adds this uninformative stream to the supervised one. The sum's benign tail is heavier than either stream's, so at 1 % FPR the threshold rises, and attacks that carry only supervised evidence fall below it.
   * Max fusion (+0.215) and the classifier alone (+0.237) lose much less.
4. **Refreshing the stale reference helps but breaks the budget.** Adding target-day benign flows to the kNN reference (recal+ref) raises the novelty stream's AUROC to 0.73–0.76 and Aegis-OSR known recall to 0.435 (W = 2,000) and 0.532 (W = 5,000). However, the realized FPR is then 2.6 % and 2.4 % — over the 1 % budget. This is plausibly within-day drift between the early warm-up window and the rest of the day, but it has not been tested.

**The same fusion rule ranks first in-distribution and last under cross-network shift.**
* LOAFO zero-day recall: Fisher 0.706 > omnibus 0.614 > max 0.531 > XGB 0.490 > XGB+Energy 0.457.
* 2018 known recall after recal@2000: XGB+Energy 0.433 > XGB 0.325 > max 0.303 > omnibus 0.266 > Fisher 0.088.

The metrics differ (zero-day vs known recall), so this is an ordering result, not a like-for-like effect size. Under within-network temporal shift (Mon–Thu → Fri), Fisher still leads (recal@2000: 0.429 vs XGB 0.367; Table IV), so the inversion is specific to the cross-network setting.

**Where nothing separates.** Some days are a hard floor rather than a recalibration problem:
* 2018-02-21 is the benign-label anomaly.
* The Infiltration days (02-28, 03-01) are near chance for every method. Infiltration is the only "unseen" 2018 family and is documented as label-noisy, so **2018 zero-day recall is not a meaningful zero-day test**.

**Mechanism status.**
* Points 1, 2 and the inversion are read directly from records.
* The *dilution* account of the Fisher loss (point 3) is an inference from aggregate metrics. Per-flow component scores were not stored, so it has not been observed directly.
* Confirming it requires the score dump in R3 (R3_PROTOCOL.md §8).

---

## 4. Verdict

| Question | CLOSR | FIRCE |
|---|---|---|
| Solves the same problem as Aegis-OSR? | Same problem class (zero-day/open-set NIDS); different evaluation question | No (closed-set drift rejection) |
| Has a calibrated false-alarm guarantee? | No | Claimed but not valid (in-sample calibration) |
| Tests under temporal / cross-network shift? | No | Cross-dataset accuracy only; no FPR, no unknowns |
| Measures detection after label-light recalibration? | No | No |
| Must be cited and positioned against? | Yes — and run head-to-head in R3 | Yes — and its validity flaw stated factually |

**Bottom line.**
* **Not distinct:** "conformal NIDS", "zero-day NIDS on CICIDS2017", and "conformal drift handling for IDS" each have prior work (B17, CLOSR, FIRCE / Transcend). None of them can be the paper's claim.
* **Not found in either paper, nor in the reviewed literature:**
  * evidence-level behaviour of a calibrated open-set detector under shift;
  * specifically, that the stale novelty stream — not the supervised evidence — causes the post-recalibration detection loss, and that the in-distribution-optimal fusion becomes the worst under cross-network shift.

  The independent novelty search (§5) narrows this further; read §5 before using this sentence.

This gap is narrow, testable and grounded in our own failure. It is the basis of Contribution 1 in `RESEARCH_GAP_ANALYSIS.md` §3 (revised).

---

## 5. Novelty re-check beyond CLOSR and FIRCE (2026-11-17)

A targeted search (2023–2026) found close work that the 61-paper review did not include. The full list and each paper's verification status are in the addendum of `STATE_OF_THE_ART_REVIEW.md` (F1–F9). Four results change what Aegis-OSR may claim:

| Finding | Effect on our claims |
|---|---|
| **Frontiers in AI 2026 (F2)** already shows that conformal validity collapses on CIC-IDS2017 ↔ CSE-CIC-IDS2018 and that 16 label-free adaptation methods do not fix supervised transfer (3 seeds). | "The guarantee breaks under 2017→2018 transfer" is **not new**. It is a replication on our side. What F2 does not measure: realized FPR at a fixed α, threshold recalibration on target benign, recall at matched FPR, novelty/fusion evidence, unseen families, per-day windows. F2 also treats the shared CICFlowMeter family as "isolating temporal drift from tooling artifacts". The extractor attribution (Contribution 2) tests exactly that assumption. |
| **Conformal FPR bounds for zero-day NIDS** exist in at least B17 (O-RAN workshop), ConFID (F5) and HADAR-UAV (F7). | "Conformal false-alarm control for NIDS" is **done** (as R2 already concluded). |
| **Conformal evidence combination with a Type-I guarantee** exists outside NIDS (MaSF, F3). Bates et al. (B11) show that naive Fisher combination of dependent conformal p-values is invalid. | Aegis's sum of surprisals, re-calibrated on a disjoint benign split, is valid because the *sum* is calibrated, not combined as p-values. It is an engineering construction, not a statistical novelty. The paper must say this and cite MaSF and Bates et al. |
| **Mondrian triage with leave-one-family-out on CIC-IDS2017**, comparing probability-space vs feature-space novelty (F4), and **hybrid fusion at a fixed FPR budget** (F6) — snippets only. | The Mondrian attribution (N9) and the hybrid design (N2) are **not** distinct until F4 and F6 are read. F4 may also already report that the two novelty types are "family-dependent and not interchangeable" in-distribution. That is close to, but not the same as, our *cross-network* inversion finding. |

**Revised bottom line.**

What remains distinct, to the extent we could check, is narrower than R2 suggested. It is the *evidence-level* account of what label-light recalibration can and cannot restore under cross-network shift:

* recall at matched FPR as the honest transfer metric;
* the supervised stream survives (high target AUROC) while the benign-referenced novelty stream goes stale;
* the in-distribution-optimal fusion is the worst after recalibration;
* refreshing the reference recovers recall but breaks the budget.

None of F1–F9, CLOSR or the 61 reviewed papers report this. **However, F4 and F6 have not been read in full.** No novelty statement goes into the paper until they are.
