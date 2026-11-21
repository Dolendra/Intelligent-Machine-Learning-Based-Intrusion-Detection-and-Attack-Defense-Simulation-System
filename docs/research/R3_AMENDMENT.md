# R3 amendment: reduced campaign, protocol fixes and pre-registration (Phase 4)

**Status:** pre-registered before any confirmatory record exists. It amends `R3_PROTOCOL.md`; anything not changed here
still applies.

| | |
|---|---|
| Branch | `research/phase4-11-completion` |
| Date | 2026-11-22 |
| Approval | The user's instruction of 2026-11-22, "complete the entire project end to end", is taken as approval of this amendment and of the reduced campaign. It is recorded here because the roadmap requires approval before R3 runs. |

**Re-scoped question.** Following Phase 2 (`RESEARCH_INTEGRITY_REPORT.md` §6), the question is:

> When does fixed fusion of supervised and novelty evidence help or hurt open-set detection at a matched false-alarm rate,
> across supervised evidence models, with family- and day-level uncertainty?

R3 measures this question. It does not propose a detector, and it claims no novelty for the recalibration finding, which
is prior work (Şahin & Mert 2026).

---

## 1. Protocol fixes (PR-01 to PR-04)

| Item | Implementation | Test |
|---|---|---|
| **PR-01** (RES-2) | `ConformalCalibrator.pvalue_smoothed` adds randomised tie-breaking, which makes `P(p ≤ α) = α` exact under exchangeability. `AegisOSR(pvalue_mode="smoothed")` uses it as the primary rule and keeps the deterministic p-values as a sensitivity check (`pdet__*` in the score dumps). The default stays `"deterministic"`, so the regression gate and history are unchanged. | `tests/test_r3_amendment.py`: exact rate under heavy ties; smoothed ≤ deterministic; reproducible draws |
| **PR-02** (RES-10) | `scripts/73_freeze_r3_configs.py` writes `research_artifacts/r3/configs/frozen_configs.json` and refuses to overwrite it. `--campaign` refuses to start without the file. The temporal protocol is added to the runner. | refusal and no-overwrite tests |
| **PR-03** (RES-18) | **Names:** the campaign runs every model, `xgb_ref` included, with one method set, `R3_METHODS` (arm B = "Closed-set (sup only)"; arm C = Fisher / max / omnibus; kNN alone). **Leakage:** the checker also reports feature-only (label-ignored) overlaps. These are informational, not fatal. **Data volume:** the early-stopped models (xgb, lgbm, catboost) fit on 90 % of the training split; dt, rf, et and xgb_ref fit on 100 %. This asymmetry is documented, not equalised. | unified-names and feature-only-hash tests |
| **PR-04** (RES-6) | New protocol `cross_loafo` (`research/protocols.cross_loafo`). For each family F in both datasets (Bot, BruteForce, DDoS, DoS, WebAttack), F is removed from every CICIDS2017 split. Evaluation is on each CSE-CIC-IDS2018 day that contains F, with independent per-day warm-up as in `cross_perday`. No design decision has ever used F's 2018 flows as unknowns. | held-out-family and unknown-labelling test |

**Also added: the staleness screen** (`research/protocols.stream_screen`). It is the exceedance rate e_j of each stream on
the first 500 benign warm-up flows, using the *source* calibration maps (α₀ = 5 %). It is recorded in every
`cross_perday` and `cross_loafo` record for the reliability study (§5).

## 2. Reduced design (deviations from R3_PROTOCOL)

| Item | R3_PROTOCOL | Amended | Reason |
|---|---|---|---|
| Seeds | 101–110 | **101–105** | Schedule. Paired t-test is primary; the minimum exact Wilcoxon p at S = 5 is 0.0625 (stated). |
| Models | 8 + TabICL | **xgb_ref, dt, rf, et, xgb, lgbm, catboost** (7) | TabM and CLOSR need the GPU campaign (≈ 88 GPU-h). CLOSR Stage 1 is blocked by the LycoS licence hold. Both are deferred, not dropped from the plan. |
| Tuning | 30 Optuna trials | **0 trials for every model** (library defaults; xgb_ref = v3 configuration) | Budget (25–60 CPU-h). The defaults arm was already required. Equal budget is kept. |
| Protocols | P1–P4 | **loafo, temporal, cross_perday, cross_loafo** | cross_loafo added (PR-04). The whole-sample `cross` is dropped: per-day supersedes it (R1b). |
| Warm-up windows | 500, 2000, 5000 | **2000** (recal and recal+ref) | The Phase 2 findings are at W = 2000. In the per-day protocols the evaluation pool is the day minus its first 2,000 benign flows. |
| Method set for xgb_ref | full v3 set (11 methods) | **R3_METHODS** in the campaign | PR-03. The v3 set stays regression-gated separately (`scripts/65`). |
| Ablations | §9 list | none confirmatory | The no-port ablation (RES-12) is exploratory if time allows. |

## 3. Metrics

* **Primary: matched-FPR TPR.** The TPR at exactly 1 % benign FPR, with the threshold set on the record's test benign
  flows. It uses each method's continuous fused score (`fused__<method>` in the dumps), exactly as in
  `scripts/72_matched_fpr_reanalysis.py`. It is labelled "oracle-matched" and used for comparisons only, never as a
  deployable operating point.
* **Secondary: conformal recall.** Recall at α = 1 % with smoothed p-values, with the realised FPR beside it. The
  deterministic-rule values are reported as a sensitivity check.
* **Targets per protocol:**
  * **loafo:** zero-day TPR on the held-out family (Infiltration and Heartbleed stay in the unknown group, as before).
  * **temporal:** unknown and known TPR.
  * **cross_perday:** known-family TPR, on days with known-family attacks.
  * **cross_loafo:** TPR on the held-out family F.
* **Variants:** per-day protocols use `recal@2000` for the confirmatory tests; `none` and `recal+ref@2000` are
  descriptive.

## 4. Statistics and pre-registered hypotheses

* **Unit:** the seed. Folds, families and days are averaged within each seed first.
* **Tests:** two-sided paired t-test over the 5 seeds (primary), Wilcoxon signed-rank (sensitivity), Holm correction
  across the 7 models within each hypothesis.
* **Uncertainty:** hierarchical bootstrap (folds or days, then seeds; 10,000 replicates; seed 20261122) as the
  uncertainty statement, as in Phase 2.
* **Everything not listed below is exploratory.**

| ID | Hypothesis (Δ = Fisher fusion − arm B, matched 1 % FPR) | Supported if | Rejected if |
|---|---|---|---|
| **A1** (amends R3-H1) | LOAFO: Δ zero-day TPR > 0 for each evidence model | ≥ 5 of 7 models with mean Δ > 0 and Holm p < 0.05 | ≤ 2 of 7. The LOAFO gain is then model-specific. |
| **A2** (amends R3-H2) | Evidence-model choice matters inside Aegis-OSR (arm C Fisher, LOAFO) | some model differs from xgb_ref by \|Δ\| ≥ 0.03 with Holm p < 0.05 (6 comparisons) | every model is TOST-equivalent to xgb_ref within ±0.02 |
| **A4** (amends R3-H4, PR-01) | Validity: under LOAFO, realised FPR with smoothed p at α = 1 % lies in [0.8, 1.2] % (seed mean), for every model, in arms B and C | all | any failure stops interpretation (calibration bug) |
| **A5** (amends R3-H5, discovery data) | cross_perday recal@2000: Δ known TPR < 0 | ≥ 5 of 7 models with mean Δ < 0 | ≤ 2 of 7. The inversion is then model-specific. |
| **A6** (new, PR-04, design-free) | cross_loafo recal@2000: sign of Δ held-out-family TPR. No direction is pre-committed. | "LOAFO gain transfers": ≥ 5 of 7 models with Δ > 0 and Holm p < 0.05. "Reverses": ≥ 5 of 7 with Δ < 0 and Holm p < 0.05. | otherwise "setting- and model-dependent" |
| **A7** (H1c bar) | cross_perday recal@2000: max fusion is non-inferior to arm B (known TPR, margin 0.02, one-sided TOST at 0.05) | ≥ 5 of 7 models | ≤ 2 of 7 |

The temporal results, conformal-recall comparisons, recal+ref and per-family breakdowns are **exploratory**.

## 5. Phase 6 reliability study: pre-registered tests (run on the R3 records and dumps)

All tests use the cross_perday and cross_loafo records at seeds 101–105.

* **Screen statistic e_j:** §1, the source-calibrated exceedance on the first 500 benign warm-up flows.
* **Stream target AUROC:** benign vs all attacks of that day, on the raw stream score, variant `none`.

| ID | Hypothesis | Supported if | Rejected if |
|---|---|---|---|
| **RS1** (replicates H1b on new seeds and models) | Across (protocol, day, seed, stream), e_j is negatively associated with the stream's target AUROC. The kNN stream counts once per (day, seed); the sup stream once per model. | Spearman ρ ≤ −0.5, and the day-cluster bootstrap 95 % CI excludes 0 | \|ρ\| < 0.3 |
| **RS2** | e_knn predicts the fusion loss: Spearman(e_knn, Δ) across (model, day, seed), where Δ = Fisher − arm B TPR on all of that day's attacks at matched 1 % FPR after recal@2000 | ρ ≤ −0.5, and the day-cluster CI excludes 0 | \|ρ\| < 0.3 |

**Phase 7 gate.** A gated method is built only if **both RS1 and RS2 are supported**. It would use only existing
components: use arm B when e_knn > 2α₀, otherwise Fisher. It is not a new learning algorithm.

**Amended H1c, which applies if the gate opens:**
* On cross_perday and cross_loafo, the gated method's matched-FPR TPR must be at least that of the **best fixed
  alternative** (max fusion and arm B) for ≥ 5 of 7 models.
* On LOAFO it must stay within −0.02 of Fisher (TOST).

Any support is labelled **development-data only**. The confirmation targets (NF-v3, LycoS) are not available without
downloads that remain on hold.

**If the gate stays closed,** Phase 7 is closed as "hypothesis not supported". The negative result is reported, and
Phase 8 validates the R3 findings instead.

## 6. Failure criteria (any one stops interpretation)

* any leakage check fails;
* A4 fails for xgb_ref;
* a protected-artifact hash changes;
* warm-up and evaluation flows overlap.
