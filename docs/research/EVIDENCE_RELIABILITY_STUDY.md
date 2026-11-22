# Evidence-reliability study and the Phase 7 decision (Phases 6–7)

**Status:** the confirmatory tests RS1 and RS2, pre-registered in `R3_AMENDMENT.md` §5, are **both rejected**. The Phase 7
gate stays **closed**: no gated or adaptive fusion method was built. This is reported as a negative result.

| | |
|---|---|
| Question | Can the reliability of each evidence stream on a new network be estimated **from benign traffic alone** (no attack labels), well enough to decide when fixed fusion should be dropped? |
| Motivation | The fusion inversion (paper §IV, R3 A5): after same-day recalibration, Fisher fusion detects fewer known-family 2018 attacks than its own evidence model. If a label-free screen could predict when this happens, a simple gate (arm B when the kNN stream looks stale, Fisher otherwise) would follow. |
| Data | cross_perday and cross_loafo records of the R3 campaign: 6 models × seeds 101–105 × 18 day/family-day folds |
| Source | `research_artifacts/r3/analysis/campaign/reliability.json` (`scripts/74_r3_analysis.py`) |

## 1. The screen

For each stream j (supervised and kNN), **e_j** is the share of the first 500 benign warm-up flows of a 2018 day whose
p-value under the **source** (CICIDS2017) calibration map is ≤ α₀ = 0.05 (`research/protocols.stream_screen`). Under
exchangeability with the source, e_j ≈ 0.05. It needs only benign traffic, which a deployment must collect anyway to
recalibrate.

## 2. Pre-registered tests and results

Spearman ρ with a day-cluster bootstrap 95 % CI (10 day clusters).

| ID | Test | Supported if | n | ρ | 95 % CI | Verdict |
|---|---|---|---|---|---|---|
| **RS1** | e_j vs the stream's AUROC (benign vs all attacks of the day, no recalibration) | ρ ≤ −0.5 and CI excludes 0 | 630 | **−0.161** | [−0.51, +0.27] | **rejected** (\|ρ\| < 0.3) |
| RS1, supervised stream only | (descriptive breakdown) | | 540 | −0.019 | [−0.38, +0.38] | |
| RS1, kNN stream only | (descriptive breakdown) | | 90 | −0.395 | [−0.87, +0.49] | |
| **RS2** | e_knn vs the fusion loss Δ = Fisher − arm B TPR on all attacks of the day, matched 1 % FPR, after recal@2000 | ρ ≤ −0.5 and CI excludes 0 | 540 | **+0.200** | [−0.30, +0.62] | **rejected** (\|ρ\| < 0.3; wrong sign) |

**Phase 7 gate.** The rule was "build the gated method only if RS1 and RS2 are both supported". Neither is, so the gate
is **closed**.

## 3. Why the screen fails (descriptive, post hoc)

The kNN screen saturates. With the source calibration, e_knn (xgb_ref, mean over seeds) lies between **0.62 and 1.00** on
every 2018 day, against 0.05 under exchangeability (`reliability.json → knn_screen_by_fold_xgb_ref`). Every day looks
"stale" to the kNN stream, including 2018-02-22 and 2018-02-23, where fusion does not hurt (xgb_ref A5 per-day Δ +0.02 and
+0.04, `hypotheses.json → A5.per_model.xgb_ref.per_fold`). A screen that flags every day cannot rank days by how much
fusion will cost, so the proposed gate would reduce to "always use arm B on a new network". That rule follows directly from
A5 and needs no screen.

The kNN-only breakdown of RS1 points in the expected direction (ρ = −0.40), but its interval is wide (90 points, 10
clusters) and includes zero. It was not a pre-registered test.

## 4. What the evidence does and does not show

* **Shown:** with these two streams and this screen, benign-only exceedance does **not** predict on which days fixed
  fusion helps or hurts. No label-free fusion gate is supported by the development data.
* **Not shown:** that stream reliability is unpredictable in general. Other screens (for example, reference-set
  refresh before screening, or distance-distribution tests rather than exceedance) were not tested. The exploratory
  recal+ref result in `R3_RESULTS.md` §4 is a lead for future work, not a finding.
* **Consequence for the framework:** no new detector or gating module was added to `framework/`. The framework ships
  the measured components only (`docs/FRAMEWORK.md`).

## 5. Phase 7 record

| Item | Decision |
|---|---|
| Gated method ("arm B when e_knn > 2α₀, else Fisher") | **not built** (gate closed by pre-registered rule) |
| Amended H1c | not tested (it only applies if the gate opens) |
| New ML algorithm | none (as required) |
| Phase 8 | validates the R3 findings instead (`R3_RESULTS.md` §3) |
