# ML pipeline and research-methodology audit

**Date:** 2026-11-18 (Phase 0 audit, read-only).
**Audited code:** `v3-openset-research` @ `440dec4c23a24e48c79b8e01f851a4984cedc26b`. This contains `main` @ `775e9a9`, which is the frozen v1.1 pipeline plus productionization.
**Method:** two independent reviewers (production ML; research methodology) traced the code and ran read-only probes. The probes used committed samples, the leakage-free replay pool, committed result JSONs and the local per-flow score dumps. The audit lead re-ran the key probes (ML-2, ML-4) and re-verified every Critical/High finding and its file:line against the source with `grep -n`.
**Not done:** no training, no raw-dataset loading and no new experiments. Nothing in the repository was modified.

**Labels used in this document**

* **Kinds of finding:**
  * **Confirmed defect:** reproduced, or deterministic from the code.
  * **Potential risk:** depends on conditions that were not exercised.
  * **Recommendation:** not a defect.
  * **Unverified assumption:** a claim that the audit could neither confirm nor refute.
* **Confidence:**
  * **EXEC:** confirmed by execution.
  * **READ:** confirmed by reading the code.
  * **SUSP:** suspected.

---

## Part A — Production ML pipeline (frozen v1.1 detector + served Zero-Day Gate)

### A.1 Lifecycle trace

| # | Stage | Where | What happens | Verdict |
|---|---|---|---|---|
| 1 | Load | `ml/preprocessing/dataset.py` (load); `config.yaml:8-12` | Every `MachineLearningCVE/*.csv` is loaded and column names are stripped. Seed 42; sample_frac 1.0. | OK |
| 2 | Identifier drop | `config.yaml:18-23` | Drops Flow ID, IPs, Timestamp and **Source Port**. **Destination Port is kept** (ML-10). | Finding |
| 3 | Labels | `dataset.py` label map | Labels are mapped to 7 families. `is_attack = Label != BENIGN`. | OK |
| 4 | Cleaning | `dataset.py` | to_numeric, inf→NaN, `dropna`, then `drop_duplicates` on features+Label. This runs **before** the split. | OK. No exact-duplicate leakage. |
| 5 | Rare classes | `dataset.py`; `scripts/01_prepare_data.py` | Labels with fewer than 50 rows are dropped: Infiltration (36) and Heartbleed (11). | OK; documented |
| 6 | Split | `dataset.py` | Stratified random 70/10/20 split, seed 42. Sizes 1,764,525 / 252,075 / 504,151. | IID split, which is optimistic (ML-20) |
| 7 | Scaling + selection | `ml/features/pipeline.py`; `scripts/02_train_models.py` | StandardScaler and SelectKBest(k=40) are fit on **train only**. A second selector for the family stage is fit on train attack rows. | OK, no leakage |
| 8 | Intensity reference | `ml/features/intensity.py` | Percentiles computed on train only. | OK |
| 9 | Model selection | `02_train_models.py:74` (val metrics); `ml/evaluation/selection.py` | Candidates are scored on **val**, at the implicit 0.5 threshold. The score includes a wall-clock latency term. | No test-based selection. Selection uses a different operating point from deployment (ML-11). |
| 10 | Test reporting | `02_train_models.py:123` (`bin_test_pred = best_binary_model.predict(X_test)`); `:151` (family test metrics) | `.predict()` means threshold **0.5**. Family metrics are computed on **true attack rows only**. | Mislabelled downstream (ML-1, ML-2) |
| 11 | SHAP background | `02_train_models.py:162` | 200 train rows in the **binary**-selected feature space. | Wrong feature space for the family model (ML-6) |
| 12 | Threshold | `scripts/15_threshold_optimization.py:78` | Sweep on validation; picks the max-F1 threshold among those with recall ≥ 0.95, giving **0.85**. | Validation only (good). Minority families were not checked (ML-2). |
| 13 | Calibration | `scripts/11_…`, `scripts/14_fit_calibrated_binary.py:50` | Script 11 evaluates an RF, not the deployed DT. Script 14 is broken on sklearn 1.9. | Inactive (ML-17) |
| 14 | Inference input | `ingestion/normalize.py:149`, `ingestion/validate.py:74`, `backend/services/pipeline.py:938` | Alias renaming, reindex to the schema, numeric coercion, NaN/Inf policy. | Order is correct (features are selected by name). Edge cases are inconsistent (ML-8, ML-9, ML-13, ML-14). |
| 15 | Prediction | `ml/prediction/predictor.py:193` (`predict_row`), `:245` (vectorised) | The same `FeatureBundle` transform as training; `p_attack ≥ 0.85` means attack, then the RF family stage. | Preprocessing is identical to training |
| 16 | Open-set gate | `backend/services/pipeline.py:253-268, 359-387`; `research/serving.py`; `security/detection_policy.py:11,27` | Every flow is scored. The default policy **union** raises an incident if either detector fires. | ML-4, ML-5 |
| 17 | Explanation | `explainability/shap_engine.py`, `lime_engine.py` | For attacks, the **family RF** is explained, never the DT that decided to alert. LIME uses a background from a different feature space. | ML-6, ML-7 |
| 18 | Risk | `security/risk/engine.py:32` | 0.5·family base + 0.25·confidence + 0.15·intensity + 0.10·asset. | ML-5, ML-16, plus architecture finding ARCH-2 |
| 19 | Rules / recommendations / planning | `security/rules`, `security/recommendations/engine.py`, `security/response/planner.py` | Advisory only. No live adapter (`adapters/live_forbidden.py`). | ML-15, ML-23 |

**Provenance.** The binary, multiclass and feature-bundle hashes (and the processed train parquet) match `model_metadata.json` (EXEC). The 78-feature list is identical, in the same order, in the schema JSON, `meta.json`, the bundle and `demo_flows.json` (EXEC). All four branches carry frozen v1.1 files that are byte-identical to tag `v1.1-research`.

**Demo and replay data.**
* `research_artifacts/replay/replay_pool.parquet` excludes every row in either model's train/val set (exact float32 key; asserted by `tests/test_replay_pool_integrity.py`).
* All 7 `demo_flows.json` vectors match test rows and no train or val rows (EXEC).
* **No train overlap in served demo or replay data.**

### A.2 Findings

#### ML-1 — High — Confirmed defect — The published "Decision Tree @ 0.85" binary test metrics were computed at threshold 0.5
* **Where:** `scripts/02_train_models.py:123` `bin_test_pred = best_binary_model.predict(X_test)` (argmax, i.e. 0.5). Propagated by `scripts/13_write_model_metadata.py` into `model_metadata.json`, where `test_metrics_binary` sits next to `binary_threshold: 0.85`.
* **Labelled as 0.85 at:**
  * `docs/PROJECT_REPORT.md:190` ("Binary test results (Decision Tree @ 0.85)": F1 0.99048, recall 0.99700, FP/FN 1,377/255)
  * `docs/research/publication/TABLES.md:39`
  * `docs/GENERALIZATION.md`
  * `docs/VIVA_QA.md`, `docs/PRESENTATION.md`
  * `frontend/src/pages/ModelsPage.tsx:364` ("Binary detector at the operating threshold")
* **Evidence (EXEC, audit lead):**
  * `threshold_sweep.json` (validation): at 0.5, recall 0.99703, F1 0.99051, FPR 0.00327; at 0.85, recall 0.99245, F1 0.99404, FPR 0.00088.
  * The test metrics in `model_metadata.json` (recall 0.99700, FPR 0.003286) match the **0.5** row.
  * No artifact contains test-split metrics at 0.85.
* **Impact:**
  * Every headline binary number describes an operating point that is not deployed.
  * At 0.85 the deployed detector has about 4× lower FPR but lower recall, and a large effect on minority families (ML-2).
  * `tests/test_productionization_p10_generalization.py` locks in the 0.5 figure as "iid_test".
* **Remediation:**
  * Score the test split once at the validation-chosen threshold, in a new script that writes new artifacts without touching frozen files.
  * Report both operating points with explicit labels, and correct the docs and UI.
* **Verification test:** a test asserting that `test_metrics_binary` records the threshold it was computed at and that this equals the deployed threshold.

#### ML-2 — High — Confirmed defect (reporting) — At the deployed 0.85 threshold, WebAttack detection falls from 98.7 % to 41.6 % and Bot from 79.3 % to 58.5 %; the headline family metrics hide this
* **Where:**
  * The threshold rule `scripts/15_threshold_optimization.py:78` maximises *overall* F1, which DoS and DDoS dominate.
  * Family metrics are computed on oracle attack rows (`02_train_models.py:151`).
  * The claims at `docs/PROJECT_REPORT.md` (macro-F1 0.998 as system performance) and the README "Sample evaluation".
* **Evidence (EXEC, re-run by the audit lead, leakage-free replay pool):**

  | family | n | detected @0.5 | detected @0.85 |
  |---|---|---|---|
  | Bot | 82 | 0.7927 | 0.5854 |
  | WebAttack | 77 | 0.9870 | 0.4156 |
  | DoS | 700 | 0.9971 | 0.9943 |
  | BENIGN (FPR) | 8000 | 0.0032 | 0.0009 |

  * The committed demo vectors `by_label.Bot` and `by_label.WebAttack` are classified BENIGN (p_attack 0.764 and 0.657).
  * The CI tests check only the DDoS demo.
* **Impact:**
  * The deployed system misses most web attacks and about 40 % of bot flows.
  * "Macro-F1 0.998" measures the family RF after a perfect stage 1, not the deployed two-stage system.
  * This is not leakage. It is a claim that does not describe what is deployed.
* **Remediation:**
  * Add per-family recall floors (or macro-recall) to the validation threshold rule, or use per-family thresholds. This would be a **new** model version; the frozen baseline is not touched.
  * Report end-to-end per-family detection.
  * Test every family's demo vector.
* **Verification test:** an end-to-end per-family detection test on the replay pool with documented floors.

#### ML-3 — High — Confirmed defect — The "temporal generalization" result (Friday F1 0.99770) scores rows the model trained on
* **Where:**
  * `scripts/25_temporal_holdout_eval.py:39` reads the raw day CSVs (`pd.read_csv`) and never excludes train/val rows. The training split is a random split across all days, so about 70 % of Friday rows are training rows.
  * The 0.5 IID figure is compared with Friday at 0.85 (`scripts/41_generalization_report.py`).
  * Claims: `docs/GENERALIZATION.md:16` ("temporally separated from its training data"), `docs/PROJECT_REPORT.md`, `docs/VIVA_QA.md`, `generalization_report.json` conclusions.
* **Evidence (READ):** the code path as above. Only `README.md:96` (v3 section) acknowledges that script 25 "re-scored models that had trained on Friday rows". The P10 documents carry no caveat.
* **Impact:** the P10 generalization claim on `main` is not evidence of temporal generalization.
* **Remediation:** mark P10 as superseded in those documents, or restrict script 25 to `test.parquet` rows and compare at one threshold. The research track's day-ordered temporal protocol is the valid replacement.
* **Verification test:** assert that the script's evaluation rows are disjoint from `train.parquet` and `val.parquet`.

#### ML-4 — High — Confirmed defect (claim vs behaviour) — The "advisory" Zero-Day Gate raises incidents under the default `union` policy, raising the benign incident rate about 9×
* **Where:**
  * `config.yaml:200` (`incident_policy: union`)
  * `security/detection_policy.py:11` ("``union`` — either detector raises an incident (default)")
  * `backend/services/pipeline.py:359-387`
* **Claims:** `README.md:100` "Production Zero-Day Gate (advisory)"; the `config.yaml` comment "advisory second detector".
* **Evidence (EXEC, re-run by the audit lead, 8,000 held-out benign flows):** benign incident-trigger rate is 0.000875 for frozen alone, 0.0075 for the gate, and **0.008125 for union**.
* **Impact:** the documented false-alarm rate (frozen, about 0.09 %) is not the system's incident rate (about 0.8 %). Gate-only incidents feed response planning.
* **Remediation:**
  * Document the policy and the combined FPR, or default to `frozen` (gate recorded only).
  * Report system-level FPR per policy.
* **Verification test:** a policy-level FPR test on the replay pool for each policy value.

#### ML-5 — Medium — Confirmed defect — Gate-only incident risk uses intensity 0 and cannot exceed MEDIUM
* **Where:** `backend/services/pipeline.py:381` passes `(payload.get("risk_factors") or {}).get("intensity")`. For a frozen-BENIGN verdict, `security/risk/engine.py:63` hard-codes `"intensity": 0.0`.
* **Evidence (EXEC, reviewer):** Heartbleed has true intensity 0.651 but 0.0 is passed. Risk comes out 55.8 (MEDIUM) instead of 65.5 (HIGH). The maximum possible gate-only score is 60.0, below the HIGH cut of 61.
* **Note:** the stored score is additionally 0 because of ARCH-2 (wrong dictionary key).
* **Remediation:** pass the measured intensity.
* **Verification test:** a gate-only incident gets intensity > 0 and the correct band.

#### ML-6 — Medium — Confirmed defect — LIME explains the family model using a background from the binary feature space, explains argmax instead of the predicted class, and misattributes features
* **Where:** background saved at `scripts/02_train_models.py:162`; `explainability/lime_engine.py` (class = argmax; substring name matching).
* **Evidence (EXEC, reviewer):**
  * The binary and multiclass selected features overlap in 27 of 40, with only 4 in the same position. So 36 of 40 perturbation columns use the statistics of a different feature.
  * For the WebAttack demo vector (predicted BENIGN), LIME explains ATTACK.
  * `Fwd Header Length.1` weights are written onto `Fwd Header Length`.
* **Impact:** LIME output for attacks is unreliable. Any XAI-agreement figure that uses LIME inherits the error.
* **Remediation:**
  * Save a separate background for each stage.
  * Explain the predicted class.
  * Map features by index (`as_map()`).
* **Verification test:** for a fixed vector, the LIME feature names equal the multiclass-selected names and the explained class equals the prediction.

#### ML-7 — Low — Confirmed — Attack explanations never explain the decision to alert
`explainability/shap_engine.py` and `lime_engine.py` explain the family RF when `pred.is_attack`. The stage-1 DT decision, which carries the false-positive risk, has no local explanation.

**Fix:** return both the stage-1 and stage-2 explanations, or state which model is being explained.

#### ML-8 — Medium — Confirmed defect — NaN/Infinity handling differs on every path; `/api/predict` returns 500
* **Where:**
  * Training drops non-finite rows.
  * The frozen predictor has no handling, so it raises ValueError.
  * The `/api/predict` schema accepts NaN/Infinity, but `backend/routes/api.py:353` catches only `FeatureValidationError` (and RuntimeError), so the generic 500 handler responds.
  * CSV/PCAP ingest rejects the whole file on a single non-finite cell (`ingestion/validate.py:74`).
  * The gate silently maps NaN/Inf to 0 (`research/serving.py:93`).
* **Evidence (EXEC, reviewer):** `Input X contains NaN` → 500; an Infinity cell → `ok=False, NaN/Inf present after numeric coercion`.
* **Impact:**
  * CICFlowMeter writes `Infinity` for zero-duration flows, so one such flow rejects a 500-row upload.
  * The two detectors see different inputs for the same flow.
* **Remediation:** one documented policy everywhere (per-row 422 with a reason, or the training-consistent treatment).
* **Verification test:** NaN, Inf and missing-value cases on every entry point.

#### ML-9 — Medium — Confirmed (mapping) / Unverified assumption (tool header format) — Python `cicflowmeter` snake_case headers do not map to the schema
* **Where:** `ingestion/cicflowmeter_runner.py:37` invokes the PyPI `cicflowmeter` CLI. `ingestion/normalize.py:149` (`_norm_key`) lowercases and collapses spaces but does not treat `_` as a space.
* **Evidence:** `rename_columns_to_schema(['dst_port','flow_duration',…])` leaves every column unchanged, giving SCHEMA_MISMATCH (EXEC).
* **Not verified:** the tool is not installed and no fixture exists, so its real header format is unconfirmed.
* **Impact:** the advertised PCAP path probably always fails. Unit and semantic parity with the 2017 Java extractor is also unverified.
* **Fix:** normalise `_`, add a real fixture, and validate the units.

#### ML-10 — Medium — Confirmed (feature use) / Potential risk (shortcut) — `Destination Port` is a model feature, while the documentation says ports were dropped
* **Where:** `config.yaml:23` drops only Source Port. Destination Port is the first selected feature for both stages.
* **Claim:** `docs/PROJECT_REPORT.md` says "ports where configured" were dropped.
* **Evidence (EXEC):** Destination Port is the top SHAP feature for the DDoS and BENIGN demo flows. The same feature is kept in research (`research/data.py:36`); see RES-12.
* **Impact:** IID scores and explanations may rely on port memorisation; transfer suffers.
* **Fix:** document it, and run a no-port ablation (research track).

#### ML-11 — Low — Confirmed
* Binary model selection ran at 0.5 and included wall-clock latency (`02_train_models.py:74`).
* DT beat XGB by 0.0023, of which latency contributed 0.00177.
* The "recall-oriented" justification holds at 0.5, not at the deployed 0.85.

#### ML-12 — Medium — Confirmed defect (claim) — P11 "measured mitigation effectiveness" (1.00 / 0.80) holds by construction
* **Where:**
  * `empirical/controlled_plane.py` (in-process synthetic plane)
  * `security/response/adapters/test_network.py:190` (`allow_fraction: 0.2`)
  * `empirical/detection.py:72` (silent `label_oracle` fallback; "detected" if any one of 64 flows crosses the threshold)
* **Claims:** `docs/PROJECT_REPORT.md` ("Measured outcomes … effectiveness 1.00"), `docs/VIVA_QA.md`, and `empirical_mitigation_report.json` (measured−simulation deltas). `docs/EMPIRICAL_MITIGATION.md` itself says "1.0 by construction".
* **Impact:** these numbers validate the harness, not mitigation.
* **Fix:** relabel them "harness validation (deterministic by construction)", drop the deltas, and use per-flow detection rates.

#### Low / improvement findings (production ML)

| ID | Kind | Where (verified) | Evidence | Fix |
|---|---|---|---|---|
| ML-13 | Confirmed defect | `backend/services/pipeline.py:938` `parse_flows_csv` vs `ingestion/adapters.py` | Raw MachineLearningCVE header: direct parser reports "missing 77 columns"; the ingestion parser accepts it (EXEC). Same issue as ARCH-4. | One parser |
| ML-14 | Confirmed defect | `ml/prediction/predictor.py:75,83` (`allow_missing_features`); `docker-compose.yml:11` (`DEMO_MODE: "true"`) | Removing Destination Port with allow_missing gives BENIGN p=0.0000. `missing_features` is not returned to the client (EXEC). | Impute with train medians or refuse; always report missing features |
| ML-15 | Confirmed | `scripts/15_threshold_optimization.py`; `security/recommendations/engine.py:168` | The certainty bands are fallback constants, but the docs call them data-derived. CRITICAL severity overrides an "uncertain" prediction. | Fix the docs and the rule |
| ML-16 | Confirmed | `backend/services/pipeline.py:170`; `backend/services/decision_trace.py:37` | Risk "confidence" for an attack is the family confidence, not P(attack). Gate-only confidence = 1−p ≥ 0.99. The trace prints confidence next to the 0.85 threshold. | Use P(attack); label both numbers |
| ML-17 | Confirmed | `scripts/14_fit_calibrated_binary.py:50` | `cv="prefit"` raises on sklearn 1.9; the fallback trains new DTs. Inactive. | Fix or delete |
| ML-18 | Confirmed | `backend/services/pipeline.py:91` | `model_info` reads `config.yaml`, while the predictor uses `threshold_operating_point.json` (both 0.85 today). | Report the predictor's threshold |
| ML-19 | Recommendation | `config.yaml`, recommendations, rules, planner | Infiltration and Heartbleed are mapped but can never be predicted by the frozen model. | Mark them dead, or route them via gate evidence |
| ML-20 | Recommendation | `ml/preprocessing/dataset.py` split | A random IID split of session-correlated flows overstates performance. | Day- or group-wise split for frozen-model claims |
| ML-21 | Potential risk | `requirements.txt` (`scikit-learn>=1.3.0`) vs pickles from 1.9.0 | Only `requirements-lock.txt` pins the version, and CI installs `requirements.txt`. Older sklearn may fail to unpickle. `global_shap_summary.json` "global" uses `feature_importances_`. | Install from the lock file in CI; rename the field |
| ML-22 | Confirmed defect | `backend/services/pipeline.py:266` | Every gate exception is swallowed (`except Exception`). One malformed row nullifies the gate for the whole batch. No log or metric. | Log, count and surface `zero_day_status:"error"` |
| ML-23 | Confirmed | `security/response/planner.py:12` vs `security/recommendations/engine.py` | The DDoS plan is BLOCK_SOURCE, while the recommendation says a single-host block is insufficient. | Align |

**Simulated vs empirical vs real (verified):**
* `simulation/` is an illustrative animation driven by `config.yaml` effectiveness priors.
* `cyberrange/` is a trace-driven discrete-time **simulation** fed by **real detector verdicts** on held-out flows, resampled with replacement. The minority families are tiny: 11 Heartbleed, 36 Infiltration, 77 WebAttack, 82 Bot.
* `empirical/` is in-process emulation with deterministic outcomes.
* **No component performs real network enforcement.** The LIVE adapter is forbidden by design.

---

## Part B — Research methodology (Aegis-OSR, R1–R3)

### B.1 What was verified correct (no finding)

* **No contamination by the held-out family.** It is absent from train, validation, C1/C2 and Mondrian calibration (`research/protocols.py:176`).
* **Split-conformal calibration is correct.**
  * C1 and C2 are disjoint from each other and from training.
  * The p-value is `(1+#{cal ≥ s})/(n+1)`, upper tail, ties counted as ≥ (`research/conformal.py:6`). Verified on a synthetic example.
  * The conformal step calibrates the **fused** statistic, so Fisher's independence assumption is not needed for FPR validity.
* **Warm-up flows are excluded from evaluation** in the temporal, cross and per-day protocols.
* **Metrics are sound.**
  * The AUROC direction is fixed; there is no `max(roc, 1−roc)`, and a test enforces this.
  * The FPR denominator is benign test flows only.
* **The statistical unit is the seed.** Paired t-tests and Wilcoxon are run over seeds; fold × seed tests are kept descriptive only.
* **Every paper number traces to an artifact path** (`scripts/59_paper_numbers.py`, `research/publication.py`), and tests regenerate them.
* **Exact reproduction:** regression gate PASS. LOAFO 6,690/6,690 and per-day 61,730/61,730 values are identical (`research_artifacts/r3/regression_gate_report.json`). The isolated r3-cpu environment also passes.
* **Serving matches research.** The served gate keeps the full C2; parity with the research implementation is 0.99996.
* **The LOAFO headline survives:** zero-day recall 0.706 vs 0.490 (XGB) at a realised 1.00 % FPR, 5/5 seeds.

### B.2 Findings

#### RES-1 — High — Confirmed defect (claim) — README and AEGIS_OSR.md state an unconditional FPR guarantee and that recalibration "restores" control
* **Where:**
  * `README.md:87` ("**guaranteed benign false-alarm rate**")
  * `README.md:99` ("restores false-alarm control **without retraining**")
  * `docs/research/AEGIS_OSR.md:75` ("restores exchangeability")
* **Evidence (EXEC, committed JSONs):**
  * Per-day recal@2000 on 2018-02-28: realised FPR ≈10 % in 4 of 5 seeds.
  * recal+ref@2000 on 2018-02-20: 8.2 %.
  * Friday recal@5000: 2.57 %.
  * Whole-sample cross: 36.7 %.
  * By contrast, the paper text is correctly conditioned, and CLAIM_AUDIT flagged this wording earlier, but the fix never reached README or AEGIS_OSR.md.
* **Remediation:** use the paper's conditional wording everywhere. This is a documentation-only change and is subject to approval.
* **Verification test:** extend `tests/test_paper_claims.py` with a forbidden-phrase check over README and docs.

#### RES-2 — High (R3 readiness) — Confirmed — Conformal ties make tree-model standalone arms over-conservative, which biases R3-H1 and makes R3-H4 fail predictably
* **Where:** `research/conformal.py` (ties counted as ≥, no randomisation); `research/r3_models.py` (DT with library defaults has leaf probabilities in {0,1}); `R3_PROTOCOL.md` §11 H1/H4.
* **Evidence (EXEC):**
  * Committed LOAFO: the closed-set DT realises **0.31 % FPR at α = 1 %**.
  * R3 pilot: DT sup-only FPR 0.10 %, ZDR 0.082.
  * Synthetic probe: smoothed (randomised) p-values restore ≈α.
* **Impact:**
  * H4 ("FPR in [0.8, 1.2] % for every model") will fail for DT and probably RF/ET, which halts the study for a tie artefact.
  * H1 (Aegis > standalone) is inflated for tie-heavy models.
  * The paper's "0.241 for a decision tree" compares at unequal realised FPR. Table I shows this; the text does not.
* **Remediation:**
  * Use randomised conformal p-values `(#{>} + U·(#{=}+1))/(n+1)`, which are exactly valid, or a deterministic jitter.
  * Report recall at matched realised FPR.
  * Amend H4 **before** the campaign.
* **Verification test:** a unit test with heavily tied scores showing realised FPR ≈ α.

#### RES-3 — High — Confirmed — The paper omits the per-day "fusion inversion" and generalises from two selected days
* **Where:**
  * `docs/research/paper.tex:45` (abstract)
  * `paper.tex:137` (cross-dataset section)
  * the conclusion
  * `research/publication.py` `rd_xgb_*` facts, hard-coded to 2018-02-14 and 2018-02-16
* **Evidence (EXEC, `research_artifacts/recalibration_diagnosis.json`):**
  * After recal@2000, closed-set XGB known recall is **0.325 vs Aegis-OSR 0.088** (seed-level +0.237, 5/5 seeds).
  * The paper quotes XGB only on the two days where it is best (0.984, 0.920) and concludes the shift "moves scores … rather than removing the signal".
  * On 02-21 (DDoS), XGB AUROC is **0.499**; on the Infiltration days it is ≈0.45–0.60; on Bot and Web, recall is ≤0.01.
  * The text says "a classifier **retrained** on CICIDS2017"; it is the same 2017 model.
* **Remediation:**
  * Add the per-day XGB / max / Fisher table.
  * State the inversion.
  * Restrict the "signal survives" sentence to the days where it holds.
  * Fix "retrained".
  * This would be done together with the approved sentence replacement (decision E).
* **Verification test:** a publication test asserting that the per-day comparison table is generated and that every per-day fact comes from all days, not from a hard-coded subset.

#### RES-4 — High — Confirmed — "The inversion is specific to the cross-network setting" is contradicted by the temporal records
* **Where:** `docs/research/PRIOR_WORK_COMPARISON.md:231`; the same reasoning appears in `RESEARCH_GAP_ANALYSIS.md` Contributions 1–2.
* **Evidence (EXEC, `openset_temporal_records.json`, seed level):** at matched FPR (oracle@2000), Aegis minus XGB zero-day recall is **−0.008 on Friday** (2/5 seeds, p=0.53) and **+0.012 on Thursday**. Recal@2000 on Thursday gives −0.029 (0/5 seeds). Friday's "Fisher leads" holds only at W=2000/5000, at unequal FPR.
* **What the evidence actually supports:** the Fisher advantage is observed in-distribution (LOAFO). Under every shift tested it is neutral (temporal, matched FPR) or harmful (cross-network).
* **Remediation:** rewrite PRIOR_WORK_COMPARISON §3 and compare at matched realised FPR using the per-flow dumps, before attributing anything to "cross-network".

#### Medium findings (research)

| ID | Kind | Where (verified) | Evidence | Impact | Fix |
|---|---|---|---|---|---|
| RES-5 | Confirmed | `paper.tex` marginal theorem; recalibration with W=500 gives \|C2\|=250 | The calibration-conditional FPR has SD ≈ √(α/\|C2\|) ≈ 0.6 % at \|C2\|=250. | The per-window guarantee is weak at small W. | State calibration-conditional (PAC) bounds for the recalibration results. |
| RES-6 | Confirmed | `research/protocols.py:176-179` (all held-out rows, cap 25,000) | Bot (1,948), WebAttack (2,143) and BruteForce (9,150) are below the cap, so every seed (pilot 0, 1–5, planned 101–110) evaluates on **identical** unknown flows. The fusion rule was chosen on pilot seed 0 using those flows. | Ablation margins (+0.09 / +0.17) may be partly selection. The +0.216 over XGB is too large to be explained that way. R3's "confirmatory" LOAFO is weaker than stated. | State it. Confirm on flows never used for design (time-split each small family) or on new data. |
| RES-7 | Confirmed | `research/protocols.py` aggregation; `scripts/64_recalibration_diagnosis.py` | CIs cover seed variance only. The per-day inversion comes from 4 of 8 attack days (day-level Wilcoxon p = 0.31). No multiplicity correction is applied across 10 × 3 tests. | Generality is overstated. | Day- and family-level summaries or a hierarchical bootstrap; describe p-values as conditional on these families/days. |
| RES-8 | Confirmed (effect) / Potential risk (mechanism) | `research/openset.py` recal+ref | Reference refresh and calibration use the same window. On 02-20, Aegis FPR is 9.35 % and kNN alone 10.6 %, against 1.47 % under plain recal. | recal+ref "wins" are measured at inflated FPR. | Time-separate W_r / W_c (H1d) and add a random-sample oracle. |
| RES-9 | Confirmed | `research/protocols.py` per-day (no `warmup_oracle`) | The temporal and cross protocols have an oracle control; per-day does not. | "Early traffic resembles the rest" is untested. | Add oracle@W, with and without refresh. |
| RES-10 | Confirmed defect (R3 readiness) | `scripts/67_r3_run.py:140` (`factory(name)`, no params); `research/r3_models.py:79-80` (`space` defined, never used); `:215` (no temporal protocol) | The tuning budget in R3_PROTOCOL §7 is **not implemented**. A campaign run would compare the hand-configured XGB reference against library-default models without recording that. | The approved "equal, documented tuning budgets" cannot be met as the code stands. | Implement tuning and frozen configs before the campaign; refuse `--campaign` without them; add temporal. |
| RES-11 | Confirmed | `paper.tex:45` ("Evidence **points to** a confound…"); RESEARCH_GAP_ANALYSIS Contributions 1–2 | Nothing tests the extractor confound. "Re-scales supervised evidence" rests on 2 days. kNN AUROC is 0.81 on 02-20 and 0.96 on 03-02 but 0.05 on 02-16/02-21. | Statements exceed the evidence. | Use hypothesis wording; quote the per-day ranges. |
| RES-12 | Potential risk | `research/data.py:36` (`_NON_FEATURES` keeps Destination Port) | BruteForce (ports 21/22) gains most from kNN in LOAFO (0.886 vs 0.225). | Part of the "novelty" may be port novelty. | No-port ablation for LOAFO and cross. |
| RES-13 | Confirmed | `research/data.py` 2018 label map | 2018 DDoS includes HOIC/LOIC-UDP, which are absent from 2017 and count as "known". The only 2018 "unknown" family is the label-noisy Infiltration. | No clean test of zero-day detection under shift. | Per-fine-label reporting; tool-level known/unknown split; cross-dataset LOAFO. |
| RES-14 | Unverified assumption | `research/data.py` (`seq` = file row offset; Timestamp dropped) | Temporal order of the 2018 rows is never checked. | The within-day drift explanations may be unfounded. | Keep Timestamp; verify monotonicity; sort by time. |
| RES-15 | Confirmed (data) / Potential risk (mechanism) | `research/protocols.py` per-day warm-up filter | One attack family per 2018 day (day × family confounded). Warm-up "benign" relies on noisy labels; on 03-02, AUROC is 0.96 but recall ≤ 0.01. | Stream-reliability conclusions conflate day and family. | Contamination sensitivity tests; report day × family. |

#### Low / improvement findings (research)

| ID | Kind | Where | Evidence / fix |
|---|---|---|---|
| RES-16 | Recommendation | CLAIM_AUDIT, PRIOR_WORK_COMPARISON | The "dilution" mechanism is directly observable in the dumps: on 02-14, Fisher loses 99.3 % of XGB's detections. This is the classical Fisher vs min-p power trade-off and should be cited, not presented as new. |
| RES-17 | Confirmed defect | `scripts/51_train_zero_day_gate.py:220-221`, `52_build_replay_pool.py:102,121`, `58_model_family_comparison.py:265,281`, `61_dataset_summary.py:55` | These write PROTECTED_MANIFEST paths without `assert_writable`. The integrity test detects overwrites afterwards but does not prevent them. Fix: add the guard. |
| RES-18 | Confirmed | `research/r3_models.py` (`_EarlyStopped` trains on 90 %); `scripts/67_r3_run.py` method names and `_row_hash` | XGB-ref gets 100 % of training data while early-stopped models get 90 %. The method names differ between arms. The leakage hash includes `fine_label`. Fix: equalise or document; unify names; add a features-only hash check. |
| RES-19 | Confirmed | `research/data.py:90` (dedup keyed on `fine_label`) | Label-conflicting duplicates survive and are not counted. Fix: count and report them. |
| RES-20 | Recommendation | `research/openset.py` Mondrian | The calibration population differs from the tested population. Mondrian works in-distribution (misattribution ≤ 0.9 %) and collapses under shift (8.1 % 2018 family accuracy). State this. |
| RES-21 | Confirmed | `research/metrics.py`, `research/digest.py` | The α = 0.001 cells are structurally zero when \|C2\| < 1000. Mark them n/a. |
| RES-22 | Recommendation | docs | After recalibration, AUROC hides the operating-point failure (Bot AUROC 0.959, recall 0.003). Report TPR at 1 % FPR or partial AUROC. |

### B.3 Is fixed Aegis-OSR fusion scientifically justified under distribution shift?

**Only in-distribution.** Summary of the evidence (EXEC on committed records and seed-1 dumps):

| Setting | Supervised stream (XGB) | Novelty stream (kNN) | Fisher vs XGB alone |
|---|---|---|---|
| LOAFO (IID) | AUROC_u 0.94 | AUROC_u 0.87; weakly correlated with sup on benign (ρ ≈ 0.1–0.2) | **+0.216 ZDR**, 5/5 seeds |
| Temporal (same network) | FPR ≈1.3 % at fixed thresholds | FPR 9–11 % | Neutral at matched FPR (RES-4) |
| 2017 → 2018, fixed thresholds | FPR 4.6 %; AUROC 0.86 | FPR 60 %; AUROC 0.51–0.54 | Aegis FPR 36.7 %; AUROC 0.80 < 0.86 |
| Per-day recal@2000 | Ranking kept on 4 days; lost on 02-21 and on Infiltration days | AUROC 0.05–0.96, anti-informative on 3 days | **−0.237 known recall** |

**Why fixed fusion fails here:** Fisher summation is the most powerful combination only when every stream carries signal. It loses power when one stream is null and loses badly when one is anti-informative. Conformal recalibration fixes the threshold, not the weighting.

**Confounds the current design cannot separate:**
* flow-extractor version
* benign composition, including port mix
* label noise
* tool novelty within a "known" family
* day × family confounding
* file-order "time"
* 2017-fitted clipping

See RESEARCH_ALIGNMENT_REVIEW.md for the consequences for the research direction.
