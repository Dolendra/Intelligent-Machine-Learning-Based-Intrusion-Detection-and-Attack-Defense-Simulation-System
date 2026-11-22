# R3 results: pre-registered reduced campaign (Phases 5 and 8)

**Status:** confirmatory analysis of the hypotheses pre-registered in `R3_AMENDMENT.md` (commit `4e84358`, configurations
frozen in `5b4b472`, amendment 2 in `e9f3a0d`). Every number below is read from the artifacts named in each section;
nothing was tuned or selected after the records existed.

| | |
|---|---|
| Question | When does fixed fusion of supervised and novelty evidence help or hurt open-set detection at a matched false-alarm rate, across supervised evidence models, with family- and day-level uncertainty? |
| Models | xgb_ref (v3 XGBoost), dt, rf, et, xgb (defaults), lgbm. CatBoost was dropped for compute before any result was read (amendment 2). |
| Seeds | 101–105 (confirmatory). The seed is the statistical unit. |
| Protocols | loafo (6 families × 5 seeds), temporal (Mon–Thu → Thu/Fri), cross_perday (10 CSE-CIC-IDS2018 days), cross_loafo (8 family-day folds) |
| Records | 130 per model (30 + 10 + 50 + 40), 780 in total; 10,200 analysis rows |
| Runs | `research_artifacts/r3/runs/campaign_b` (xgb_ref, dt, rf) and `campaign_c` (lgbm, xgb, et); see "Execution" below |
| Analysis | `research_artifacts/r3/analysis/campaign/` (`scripts/74_r3_analysis.py`), validation `research_artifacts/r3/validation/campaign_validation.json` (`scripts/76_r3_validation.py`) |
| Reproduction anchor | 21,300 record values recomputed from the per-flow score dumps; max abs. difference 5.0×10⁻⁷ (records round to 6 decimals) |

Δ always means **(fusion) − (arm B)**, where arm B is the same evidence model alone, calibrated identically. The primary
metric is the detection rate at an exactly matched 1 % benign FPR (an oracle-matched threshold, used for comparison only,
never as an operating point). Brackets give the hierarchical bootstrap 95 % interval (folds or days, then seeds; 10,000
replicates, seed 20261122). *p* is the two-sided paired t-test over the 5 seeds with Holm correction across the 6 models.
At S = 5 the smallest possible exact Wilcoxon *p* is 0.0625; every Wilcoxon *p* below is therefore ≥ 0.0625. This was
stated in advance.

---

## 1. Verdicts

| ID | Hypothesis | Rule | Result | Verdict |
|---|---|---|---|---|
| **A4** | Validity: LOAFO realised FPR with smoothed *p* at α = 1 % in [0.8, 1.2] % for every model, arms B and C | all in band | 24 of 24 model × method cells in band (0.990 %–1.061 %) | **supported**: interpretation may proceed |
| **A1** | LOAFO: Δ zero-day TPR > 0 | ≥ 5 models with Δ > 0 and Holm *p* < 0.05 | **6 of 6** | **supported** |
| **A2** | Evidence-model choice matters inside Aegis-OSR (LOAFO, Fisher) | some model differs from xgb_ref by ≥ 0.03, Holm *p* < 0.05 | dt: −0.173, Holm *p* 2.0×10⁻⁵; no model TOST-equivalent | **supported** |
| **A5** | cross_perday recal@2000: Δ known TPR < 0 | ≥ 5 models with mean Δ < 0 | **6 of 6** | **supported** |
| **A6** | cross_loafo recal@2000: sign of Δ held-out-family TPR (no direction committed) | ≥ 5 significant in one direction | 0 significant positive, 1 significant negative (rf) | **setting- and model-dependent** |
| **A7** | cross_perday recal@2000: max fusion non-inferior to arm B (margin 0.02) | ≥ 5 models | **0 of 6** | **rejected** |

No failure criterion (§6 of the amendment) was triggered: every leakage check passed, A4 passed for xgb_ref, the protected
artifacts are unchanged (regression gate `research_artifacts/r3/regression_gate_report_phase4.json`: PASS) and warm-up and
evaluation flows never overlap.

## 2. Per-model effects

Source: `research_artifacts/r3/analysis/campaign/hypotheses.json`. Mean over seeds 101–105.

| Evidence model | A1 LOAFO: Fisher − B | A5 2018 per day: Fisher − B | A6 2018 cross-LOAFO: Fisher − B | A7 2018 per day: max − B |
|---|---|---|---|---|
| XGBoost (v3 ref.) | **+0.228** [+0.08, +0.42], *p* 1.2×10⁻⁵ | −0.212 [−0.44, −0.03], *p* 0.056 | −0.043 [−0.16, +0.01] | −0.022 [−0.10, +0.04] |
| Decision tree | **+0.268** [+0.06, +0.51], *p* 1.7×10⁻⁵ | −0.006 [−0.10, +0.08], *p* 0.90 | +0.022 [−0.01, +0.07] | −0.032 [−0.15, +0.08] |
| Random forest | **+0.134** [+0.04, +0.25], *p* 0.0036 | −0.126 [−0.28, +0.00], *p* 0.042 | **−0.053** [−0.16, +0.03], *p* 0.013 | −0.079 [−0.26, +0.05] |
| Extra trees | **+0.214** [+0.07, +0.38], *p* 0.0014 | −0.055 [−0.18, +0.02], *p* 0.099 | −0.046 [−0.14, +0.02], *p* 0.069 | −0.055 [−0.19, +0.04] |
| XGBoost (defaults) | **+0.247** [+0.10, +0.43], *p* 3.5×10⁻⁴ | −0.181 [−0.40, −0.02], *p* 0.051 | −0.020 [−0.06, +0.01] | −0.031 [−0.11, +0.03] |
| LightGBM | **+0.154** [+0.06, +0.26], *p* 0.0036 | −0.187 [−0.40, −0.03], *p* 0.056 | −0.025 [−0.08, +0.02] | −0.048 [−0.17, +0.04] |

(*p* is the Holm-adjusted value; A5 and A7 are decided by direction count and non-inferiority, as pre-registered.)

**Reading.**

1. **LOAFO (A1).** Fixed Fisher fusion of a supervised stream with a kNN benign-novelty stream raises zero-day detection
   at a matched 1 % FPR for every evidence model tested, by 0.13–0.27. Every model is positive on all 5 seeds and for all 6
   held-out families. Which family gains most depends on the model: BruteForce for four of the six models, DoS for dt and
   PortScan for lgbm (per-family values in `hypotheses.json → A1.per_model.*.per_fold`).
2. **Evidence model (A2).** Inside the fused detector, the evidence model matters at the extremes. The decision tree
   gives 0.173 less zero-day TPR than xgb_ref. et, xgb and lgbm are within ±0.03 of xgb_ref on average, but none is
   TOST-equivalent at ±0.02 with 5 seeds.
3. **Cross-network, per day (A5).** After same-day recalibration, Fisher fusion detects *fewer* known-family attacks than
   its own evidence model for all six models. The size varies a lot: about −0.2 for the three gradient-boosted models
   (xgb_ref, xgb, lgbm), −0.13 for rf, −0.06 for et and ≈ 0 for dt. Three of the six hierarchical intervals exclude zero
   (xgb_ref, xgb, lgbm). The direction count is
   the pre-registered rule; the per-model t-tests are not individually significant after Holm except for rf.
4. **Cross-dataset LOAFO (A6).** On 2018 days with a family that was removed from training, the LOAFO gain does **not**
   transfer: five of six means are slightly negative (−0.02 to −0.05), one is slightly positive (dt), and only rf is
   significant (negative). The pre-registered label is "setting- and model-dependent".
5. **Max fusion (A7).** Max fusion is not a safe fixed alternative either: no model is non-inferior to arm B within 0.02,
   and all six means are negative (−0.02 to −0.08).

## 3. Phase 8 validation (post hoc robustness; changes no verdict)

Source: `research_artifacts/r3/validation/campaign_validation.json`.

| Check | Result |
|---|---|
| **V1: leave one fold out.** Each hypothesis re-decided with its own rule after dropping each family or day | A1, A5 and A6 keep their verdict for every dropped fold. A7 is rejected for 7 of 8 dropped days; dropping 2018-02-20 makes it "inconclusive" (3 of 6 non-inferior). |
| **V2: replication on new seeds.** xgb_ref LOAFO gain vs the Phase 2 re-analysis (seeds 1–5) | +0.218 [+0.08, +0.40] (seeds 1–5) → **+0.228** [+0.08, +0.42] (seeds 101–105). The new mean is inside the old interval, and the per-family pattern repeats. |
| **V3: p-value rule.** Smoothed (primary) vs deterministic | Fused methods: almost identical realised FPR. Tree models' arm B: deterministic ties under-use the budget, e.g. dt arm B realises 0.10 % with the deterministic rule vs 1.01 % smoothed. This confirms PR-01. Conformal-recall Δ (LOAFO, Fisher − B) differs by ≤ 0.007 between rules. |
| **V4: metric agreement.** Sign of A1 and A5 under matched-FPR TPR vs conformal recall at α = 1 % | 6/6 and 6/6 same sign |
| **V5: anomalous day.** A5 without 2018-02-21 (the day whose "benign" flows differ sharply from every other day) | still supported |

## 4. Exploratory results (not pre-registered as confirmatory)

Source: `hypotheses.json → exploratory`.

* **Temporal (Mon–Thu → Fri).** Without recalibration, Fisher − B on unknown TPR is about 0 or negative. It is strongly
  negative for rf (−0.49) and et (−0.51); the mechanism was not tested. After recal@2000 every model is within ±0.02.
* **Reference refresh (recal+ref@2000).** When the kNN reference set is also extended with the same 2,000 benign warm-up
  flows, the per-day inversion largely disappears. On cross_perday, Fisher − B is positive for 5 of 6 models (−0.05 to
  +0.12); on cross_loafo it is positive for 5 of 6 (−0.01 to +0.13). **This is exploratory, single-campaign evidence.**
  It points at the stale kNN *reference*, not the score combination itself, as the main driver of the inversion. It needs
  its own pre-registered test before it can be claimed.
* **No recalibration (variant none) on 2018.** On cross_perday, Fisher − B is negative for every model (−0.04 to −0.35).

## 5. What the results support and what they do not

**Supported:**
* In-distribution open-set evaluation (LOAFO): fixed Fisher fusion with kNN benign-novelty evidence is a **model-agnostic**
  improvement at a matched false-alarm rate across six tree-based evidence models, and the effect replicates on new seeds.
* Under cross-network shift with same-day recalibration, the same fixed fusion **loses** known-attack detection relative to
  its own evidence model (direction consistent across all six models; size model-dependent).
* Neither fixed rule (Fisher or max) is safe to keep under shift (A5, A7).

**Not supported, or not tested:**
* No claim that the LOAFO gain transfers to unseen families on a new network (A6: it does not).
* No claim of a deployable rule for choosing between fusion and the supervised stream from benign data alone: the
  reliability study rejected both pre-registered tests (`EVIDENCE_RELIABILITY_STUDY.md`). No gated method was built.
* No neural (TabM), CatBoost, CLOSR or tuned-model results: these were not run (see `IMPLEMENTATION_STATUS.md`).
* No universal zero-day detection; no guaranteed false-alarm rate under distribution shift.

## Execution

* **Streams.** The campaign ran as parallel streams under the frozen configuration:
  * `campaign_a` (CatBoost) was stopped after 2 LOAFO folds and is **excluded** (amendment 2).
  * `campaign_b` (xgb_ref, dt, rf) was launched for all six models. By the split plan it was stopped right after rf
    completed (`campaign_b/STREAM_NOTE.json`), and its partial et dump is unused.
  * `campaign_c` (lgbm, xgb, et) ran to completion: 390 splits checked, all leakage checks pass.
* **Leakage.** The leakage checker aborts the run on any failed split, so a stream without a traceback has passed every
  check. Both logs are archived as `campaign.log`.
* **Command:**
  `python scripts/74_r3_analysis.py --run campaign_b campaign_c --name campaign --assign xgb_ref=campaign_b dt=campaign_b rf=campaign_b et=campaign_c xgb=campaign_c lgbm=campaign_c`
* **Regression gate** (LOAFO, seed 1, `--tag phase4`): historical artifacts unchanged, frozen v1.1 identical to tag,
  exact reproduction, complete score dumps, overwrite protection. PASS.
