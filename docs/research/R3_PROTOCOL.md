# R3 — Experimental protocol: tabular and open-set models, standalone and inside Aegis-OSR

**Status: PROPOSED — NOT APPROVED, NOT EXECUTED.** No package in this document has been installed for R3, no R3 model has been trained, and no R3 dataset has been downloaded. Every number below marked *estimate* is a planning figure, to be replaced by Stage-0 measurements.
**Branch:** `v3-openset-research` · **Prepared:** 2026-11-17 · **Depends on:** R1b (complete), R2 + `PRIOR_WORK_COMPARISON.md` (for review).

Rules carried over from the project (CLAIM_AUDIT §0–§8):
* frozen v1.1 artifacts untouched;
* no historical result overwritten — all R3 outputs go to new `r3_*` files;
* no test data used for selection;
* seed-level statistics;
* every published number generated from an artifact;
* the conformal FPR bound is stated as conditional on exchangeability.

---

## 0. Questions R3 answers (and the ones it does not)

| ID | Question | Type |
|---|---|---|
| Q1 | Is Aegis-OSR's in-distribution gain (LOAFO) specific to XGBoost, or does it hold for other supervised evidence models? | Confirmatory (pre-registered, §11) |
| Q2 | How does each model behave **standalone** at a calibrated operating point, versus **inside** the full pipeline? | Confirmatory |
| Q3 | How does CLOSR (closest peer-reviewed zero-day NIDS method) compare, (a) as published, on its own protocol; (b) at a calibrated α under our protocols? | (a) reproduction; (b) confirmatory, no directional prediction |
| Q4 | Does the cross-network fusion inversion (PRIOR_WORK_COMPARISON §3) hold for every supervised model? | Robustness across models on the **discovery data** — *not* confirmation of a mechanism |
| Q5 | Cost: training/inference time, latency, memory, size | Descriptive |

**Out of scope for R3:**
* Any new method (the Contribution-1 fusion fix, the attribution study and violation monitoring are separate, later protocols).
* UI work.
* Host/window features.

---

## 1. Models: official sources, versions, dependencies

All versions were checked on 2026-11-17 against PyPI and official repositories. The machine runs Python 3.11.9, which pins XGBoost to 3.2.0: XGBoost ≥ 3.3 requires Python ≥ 3.12.

| # | Model | Official source | Paper | Version to pin | License | Status on this machine |
|---|---|---|---|---|---|---|
| 1 | Decision Tree | github.com/scikit-learn/scikit-learn | Pedregosa et al., JMLR 2011; Breiman et al. 1984 | scikit-learn **1.9.0** (installed; 1.9.1 exists, do not upgrade mid-study) | BSD-3 | installed |
| 2 | Random Forest | same | Breiman, Mach. Learn. 2001 | same | BSD-3 | installed |
| 3 | Extra Trees | same | Geurts et al., Mach. Learn. 2006 | same | BSD-3 | installed |
| 4 | XGBoost | github.com/dmlc/xgboost | Chen & Guestrin, KDD 2016 | **3.2.0** (installed) | Apache-2.0 | installed |
| 5 | LightGBM | github.com/lightgbm-org/LightGBM (moved from microsoft/LightGBM, 2026) | Ke et al., NeurIPS 2017 | **4.7.0** (win_amd64 wheel; needs the VC++ runtime) | MIT | **not installed** |
| 6 | CatBoost | github.com/catboost/catboost | Prokhorenkova et al., NeurIPS 2018 (cite after checking the DOI; the repo cites Dorogush et al. 2017) | **1.2.10** (cp311 win_amd64 wheel) | Apache-2.0 | **not installed** |
| 7 | TabM | github.com/yandex-research/tabm | Gorishniy, Kotelnikov, Babenko, ICLR 2025 (arXiv 2410.24210) | `tabm` **0.0.3** + `rtdl_num_embeddings` ≥ 0.0.12, < 0.1; torch **2.12.0+cpu** (installed) | Apache-2.0 | **not installed** |
| 8 | CLOSR (+ CLAD) | github.com/jackwilkie/CLOSR @ commit **79da4d1** | Wilkie et al., IEEE TNSM 23:2064–2076, 2026, doi:10.1109/TNSM.2026.3652529 | repo pins torch 2.0.1, numpy 1.24.2, pandas 2.0.0, sklearn 1.2.2 → run in a **separate venv** with those pins for the reproduction (Stage 1); our torch 2.12 for Stage 2, recorded as a deviation | Apache-2.0 | not cloned in the repo; no pip package |
| R | TabICL (reserve) | github.com/soda-inria/tabicl | Qu et al., ICML 2025 (arXiv 2502.05564); v2: ICML 2026 (arXiv 2602.11139) | `tabicl` **2.2.0**; pin `checkpoint_version` (the v2 checkpoint `tabicl-classifier-v2-20260212.ckpt` is 110 MB, downloaded from Hugging Face `jingang/TabICL`) | BSD-3 | **not installed**; Stage-0 gate |
| — | Optuna (tuning) | github.com/optuna/optuna | Akiba et al., KDD 2019 | **5.0.x** or the last 4.x release; avoid 5.1.0 (released 2026-11-16, too new to pin) | MIT | not installed |

**Environment.**
* Create `requirements-r3.txt` with exact pins and `pip --require-hashes` hashes; never modify `requirements.txt` or `requirements-lock.txt`.
* The CLOSR reproduction runs in its own venv (`.venv-closr`, git-ignored), with the repo's pins.

**Device.**
* The installed torch is a CPU build (`2.12.0+cpu`). An RTX 4060 Laptop GPU (8 GB) is present but unused.
* The protocol is CPU-only. TabICL's default `device=None` would pick CUDA if a CUDA build were present, so every torch model sets `device="cpu"` explicitly.
* **Optional deviation (needs approval):** a CUDA torch build in a separate venv, for CLOSR and TabM only. Results would be device-tagged and checked for CPU/GPU agreement on one seed.

**Licences.** All are permissive. CLOSR's code is used unmodified except for the documented deviations in §8.3.

---

## 2. Hardware, storage and time

**Machine:**
* Intel i7-13650HX, 14 cores / 20 threads.
* 23.7 GiB RAM.
* D: has 116.5 GB free.

**Measured from existing artifacts** (all 11 current methods per record; 20 threads):
* LOAFO: 84 s per record (30 records, 42 min).
* Temporal: 50 s per record.
* Cross: 74 s per record.
* Per-day: 72 s per seed-day record.

### 2.1 Run counts

Seeds S = 10 for the cheap models and S = 5 for TabM and CLOSR (§6).

**Trained models per model type and seed:**
* LOAFO: 6 folds.
* Temporal: 2 folds.
* Cross-network: 1 model per seed, shared by the whole-sample cross protocol and the per-day protocol, because they use the same CICIDS2017 training data. *This sharing is a change from the current code, which trains separately; the shared model must equal what either protocol would train for that seed — test it.*

That is 9 fits per seed, so 90 fits per model at S = 10 and 45 at S = 5.

### 2.2 Estimated compute

*Estimates, to be replaced by the Stage-0 pilot.*

| Model | Fit time per run (est.) | Fits | Total CPU (est.) | Peak RAM (est.) |
|---|---|---|---|---|
| DT | < 10 s | 90 | < 0.5 h | 2 GB |
| RF (300 trees) | 1–3 min | 90 | 2–5 h | 4–8 GB |
| Extra Trees (300 trees) | 1–2 min | 90 | 2–3 h | 4–8 GB |
| XGBoost | 20–40 s (measured within the 84 s record) | 90 | 1 h | 3 GB |
| LightGBM | 20–60 s | 90 | 1–2 h | 3 GB |
| CatBoost (1,000 iter.) | 3–8 min | 90 | 5–12 h | 4–6 GB |
| TabM (k = 32, CPU) | 30–90 min, **unconfirmed** (paper used an A100) | 45 | 25–70 h | 4–8 GB |
| CLOSR (3×1024 MLP, batch 4096, 200 epochs, CPU) | 4–8 h, **unconfirmed** | 45 | **180–360 h — not feasible on CPU** | 6–10 GB |
| Pipeline overhead (kNN, surprisal, conformal, attribution, baselines) | about 40 s per record | 225 records | 2.5 h | — |
| Tuning (§7) | — | — | 25–60 h | — |

**CLOSR consequence.** The full CLOSR protocol is infeasible on this CPU. Options, in order of preference:
1. Approve the CUDA venv: CLOSR at 200 epochs is then *estimated* at 20–40 min per fit.
2. Keep CPU, cap at 50 epochs with early stopping on a held-out split. This is a recorded deviation, and Stage 1 is still run as published.
3. Run CLOSR only in LOAFO and per-day (not temporal or cross), with S = 5.

**Total (option 1).** About 120–200 CPU-hours, i.e. about 5–9 days of wall-clock time with runs in parallel, 3 at a time within the RAM limit.

**Storage.**
* Per-flow score dumps (§8.4), as parquet + zstd: about 15 GB.
* Model files: kept only for seed 101 (about 3 GB).
* Total under 25 GB.

---

## 3. Datasets: selection and justification

| Dataset | Role in R3 | Justification | Status |
|---|---|---|---|
| CICIDS2017 MachineLearningCVE (current) | P1, P2, and the source for P3/P4 | Comparability with every existing Aegis result | in repo |
| CSE-CIC-IDS2018, sample **v2** (`cic2018_sample_v2.parquet`) | P3, P4 targets | Cross-network; the only target where the fusion inversion was seen | in repo (cache git-ignored; rebuilt by `load_cic2018(version=2)`) |
| **LycoS-IDS2017** (Rosay et al. 2021) | Stage 1 CLOSR reproduction; P5 (optional) | CLOSR's own dataset; corrected re-extraction of the same traffic | **not downloaded; availability and licence must be verified first (needs approval)** |

**Not used in R3.** Each of these belongs to a later contribution protocol:
* LycoS-Unicas-IDS2018 (C12) and NetFlow NF-v3 (C17): kept for the Contribution-1 confirmation and the Contribution-2 attribution study.
* UNSW-NB15 and ToN-IoT: they have a different feature schema, which would add a harmonisation confound to a model benchmark.

---

## 4. Harmonisation and feature compatibility

1. **CICIDS2017 ↔ CSE-CIC-IDS2018.**
   * Use the existing mapping in `research/data.py`: 77 CICFlowMeter features via column aliases, and the duplicated `Fwd Header Length.1` dropped.
   * 2018 labels are mapped to the 2017 families (`_LABEL_MAP_2018`).
   * No new mapping is introduced in R3. The mapping file hash is recorded per run.
2. **LycoS-IDS2017 (P5, Stage 1).**
   * The schema differs (snake_case, different extractor).
   * Write a crosswalk table `research/lycos_crosswalk.csv` (LycoS column → MachineLearningCVE column → transform), reviewed before any run.
   * Unmatched features are dropped and listed.
   * Results are reported on (i) the intersection set and (ii) each dataset's full native set.
3. **Per-model preprocessing.**
   * Inside the pipeline: every model sees the identical signed-log standardised features (statistics from the training split only), so the evidence model is the only thing that changes.
   * Standalone: each model may also use its native preprocessing: none for trees, CLOSR's z-normalisation, TabM's piecewise-linear embeddings. Native-preprocessing results are a separate, labelled arm.
4. **Categorical-like columns** (`Destination Port`):
   * kept numeric for all models (current behaviour);
   * CatBoost's native categorical handling is an ablation arm only, labelled as such.
5. **CLOSR input width.** The code hard-codes `d_in=72`. For our data it becomes 77; this is a documented one-line deviation.

---

## 5. Leakage-free splits

**Per seed and fold**, all disjoint and drawn before any model sees data:

```
CICIDS2017 (de-duplicated) ──► train (60 %) ──► fit split  +  early-stop split (10 % of train, stratified)
                            ├─► validation (10 %) ──► C1 benign (surprisal, 30 k) | C2 benign (conformal, 30 k) | val attacks (Mondrian)
                            └─► test (30 %) + all rows of the held-out family (LOAFO) / the later day (temporal) / the 2018 target (cross)
```

**Split rules.**
* **Early stopping uses its own split.** GBDT/TabM/CLOSR early stopping and probability-temperature fitting use the early-stop split. They never use C1, C2 or test, so the conformal calibration stays exchangeable with test benign. *This differs from the existing XGB pipeline, which has no early stopping — keep XGB's existing configuration as the reference arm.*
* **Caps are unchanged** (`research/protocols.py`):
  * train: 300 k benign + ≤ 60 k per family;
  * validation: 60 k benign + ≤ 10 k per family;
  * test: 150 k benign + ≤ 25 k per family;
  * per-day 2018: 20 k benign + ≤ 8 k attack per day.
* **LOAFO.** The held-out family is absent from fit, early-stop, C1, C2 and the tuning data of that fold (§7).
* **Temporal.** Train/validation come from earlier days only. The test day's earliest 5,000 benign flows are the warm-up pool and are never evaluated.
* **Per-day 2018.** The warm-up is that day's earliest W benign flows; evaluation is the rest of the day. The overlap must be 0, recorded per record (as in R1b).

**Leakage checks.** These are automated, and any failure invalidates the record:
* (a) row-hash disjointness (float32 row hashing, as in the replay-pool check) across fit, early-stop, C1, C2, test and warm-up;
* (b) held-out family count = 0 in every training-side split;
* (c) no target-domain row in any tuning split;
* (d) the test-side benign count matches the cap.

---

## 6. Seeds

* **Confirmatory seeds: 101–110 (S = 10).** These are fresh, never used by any earlier design decision. TabM and CLOSR use 101–105 (S = 5) unless the CUDA option is approved.
* **Seed 0** stays the pilot/selection seed. **Seeds 1–5** are used only to reproduce the existing XGB Aegis-OSR results bit-for-bit (pipeline regression check, §12).
* **Determinism:**
  * fixed seeds and thread counts for every library: `random_state`, XGB/LightGBM `seed` + `deterministic=True`, CatBoost `random_seed`;
  * `torch.manual_seed`, `torch.use_deterministic_algorithms(True)` and `torch.set_num_threads(n)`.

  Non-determinism that remains is reported, by re-running seed 101 twice and diffing.
* **Power note.** With S = 5, the smallest exact two-sided Wilcoxon p is 0.0625, so the paired t-test is primary (§10). The LOAFO effects seen so far (+0.216 recall, sd ≈ 0.03) are detectable at S = 5. The smaller model-to-model differences expected in Q1 may not be. S = 10 gives a minimum Wilcoxon p of 0.002.

---

## 7. Tuning budgets

**Principle.** Tuning never sees unknown families, target-domain data, test data or C1/C2. The objective is **closed-set** quality on the known classes only:
* primary: early-stop-split log-loss;
* tie-break: macro-F1.

Zero-day recall is never an objective.

**Tuning task.**
* Per LOAFO fold: seed-0 split, held-out family removed, 3-fold CV on the fit split.
* Temporal and cross: the source data of that fold (Mon–Wed, Mon–Thu, or all of CICIDS2017).
* One configuration is chosen per (model, fold) and then frozen for all confirmatory seeds.

**Budget.** It is equal per model: **30 Optuna TPE trials** (sampler seed 0), with a wall-clock cap of 2 h per (model, fold), on a 200 k-row stratified subsample.

| Model | Search space (from official docs/papers where available) |
|---|---|
| DT | max_depth {4…40, None}, min_samples_leaf [1, 200] log, criterion {gini, entropy} |
| RF / ET | n_estimators 300 (fixed), max_features {sqrt, 0.3, 0.5}, min_samples_leaf [1, 50] log, max_depth {None, 20, 40} |
| XGBoost | Existing Aegis configuration = reference arm (no tuning, as published). Tuned arm: eta [0.01, 0.3] log, max_depth [3, 12], min_child_weight [1, 20] log, subsample [0.5, 1], colsample_bytree [0.5, 1], lambda [1e-3, 10] log; up to 2,000 rounds with early stopping (50) |
| LightGBM | learning_rate [0.01, 0.3] log, num_leaves [15, 255] log, min_child_samples [5, 200] log, feature_fraction [0.5, 1], bagging_fraction [0.5, 1], lambda_l2 [1e-3, 10] log; up to 2,000 rounds with early stopping |
| CatBoost | learning_rate [0.01, 0.3] log, depth [4, 10], l2_leaf_reg [1, 10] log; up to 2,000 iterations with early stopping |
| TabM | Paper space: n_blocks [1, 4] (piecewise-linear embeddings), d_block [64, 1024] step 16, lr [1e-4, 5e-3] log, weight_decay {0, [1e-4, 1e-1] log}, n_bins [2, 128], d_embedding [8, 32] step 4; k = 32 fixed; batch 1024; patience 16; gradient clip 1.0. Probabilities = mean of the k members' softmax (official README) |
| CLOSR | Stage 2 uses the repo defaults (lr 1e-5, wd 0.0404, batch 4096, 20-epoch warm-up + cosine, margin 1.0). The authors' 200-trial search is **not** repeated (budget). Recorded as "untuned on our data" |

Every model also gets a **library-defaults arm**. It is cheap, it guards against tuning artefacts, and defaults are often competitive on tabular data (McElfresh et al. 2023).

**Class weighting.** The current sqrt-inverse-frequency weights are applied to every model that supports sample weights. CLOSR uses its own balanced sampler.

---

## 8. Integration with Aegis-OSR: each model three ways

### 8.1 Arms per model m

| Arm | Score | Threshold | What it measures |
|---|---|---|---|
| **A. Native** | the model's own decision (argmax over K+1 classes) | none (closed-set) | What a user gets with no open-set machinery |
| **B. Standalone-calibrated** | s_m(x) = 1 − P_m(benign \| x) | benign surprisal on C1 → split-conformal on C2 at α (the Aegis calibration with a single stream) | The model's evidence at a guaranteed (IID) FPR |
| **C. Inside Aegis-OSR** | s_m fused with the kNN novelty stream: Fisher (primary), max, omnibus | same conformal step on C2; Mondrian attribution from m's class probabilities | The full pipeline with m as its supervised evidence |

All three arms use the same splits. Arm C with m = XGB (reference configuration) **is** the current Aegis-OSR and must reproduce existing records for seeds 1–5 exactly (§12).

### 8.2 Recalibration (P3, P4 and temporal)

Arms B and C are evaluated with no adaptation and with recal@W and recal+ref@W, W ∈ {500, 2000, 5000}, as in R1b. No retraining.

### 8.3 CLOSR specifics

**Stage 1: reproduce CLOSR's actual methodology on LycoS-IDS2017.** It needs only CLOSR's own code, data and split.

* **1a. Evaluate the released weights** (`weights/closr.pt.tar`, `weights/clad.pt.tar`) on the authors' exact split (`split_seed=39058032`, zero-day classes = classes with < 100 flows: SQL Injection and Heartbleed). Compute their metrics with their code (open-set AUROC, OpenAUC as implemented, CLAD zero-day AUROC, FPR@95).
  * **Pass:** within ±0.005 of the paper's Table I/III means (CLOSR open-set AUROC 0.9740, OpenAUC 0.9694, closed-set accuracy 0.9953; CLAD zero-day AUROC 0.9966).
  * Also report the orientation-fixed AUROC (no `max(roc, 1 − roc)`) and bootstrap CIs over flows. With about 11 Heartbleed positives, the CI is part of the result.
* **1b. Retrain from scratch** with the repo defaults: 3 seeds (the authors' 20 runs are infeasible on this CPU), torch 2.0.1 in `.venv-closr`.
  * **Pass:** each seed within the paper's mean ± 0.01.
  * A failure is reported as a reproduction failure, not hidden. Stage 2 then proceeds with the configuration that reproduced (1a weights cannot be used in Stage 2, because they were trained on a different split).

**Stage 2: CLOSR under our protocols.** It is trained from scratch per seed and fold, on our fit split. Deviations: `d_in` = 77; early stopping on our early-stop split.
* **Arm A:** argmax of Eq. 14 over benign + known families.
* **Arm B:** two variants: (i) s = 1 − P(benign | x) from Eq. 14; (ii) CLOSR's own OOD score (Eq. 16), calibrated directly as a single-stream score.
* **Arm C:** (i) as the supervised stream fused with kNN; and **C′**, kNN novelty computed in the **CLOSR embedding** instead of raw features. C′ tests whether a learned benign-anchored space fixes the stale-reference problem — an explicit ablation, not a new method.

### 8.4 Per-flow score dumps (required for mechanism analysis)

For every record, store per test flow:
* the stream scores and stream surprisals (t_sup, t_nov);
* the fused score and the p-value;
* the label and family.

Store them as parquet under `research_artifacts/r3/scores/` (git-ignored, regenerable); a committed manifest records the SHA-256 of each file. This is what allows the "dilution" account in PRIOR_WORK_COMPARISON §3 to be checked directly rather than inferred.

---

## 9. Baselines and ablations

**Baselines** (already implemented; rerun on R3 seeds):
* closed-set XGB;
* closed-set DT (v1.1 style);
* Isolation Forest;
* autoencoder;
* kNN distance;
* XGB + Energy.

**Ablations** (per supervised model m, arm C):
1. Fusion rule: Fisher / max / omnibus.
2. Novelty stream: kNN raw (default) / kNN in CLOSR embedding (C′) / none (= arm B).
3. Tail extrapolation on / off.
4. Tuned vs library defaults.
5. Native vs shared preprocessing (arms A/B only).
6. CatBoost with `Destination Port` as categorical.

**Not included:** new fusion methods (Contribution 1). R3 measures; it does not fix.

---

## 10. Metrics

Each metric is reported per record and per family, then aggregated (§11):

| Metric | Definition / note |
|---|---|
| Macro-F1 (open-set) | over K + 2 classes: benign, each known family, UNKNOWN (unknown attacks labelled UNKNOWN-ATTACK or ZERO-DAY-ANOMALY count as correct) |
| Macro-F1 (closed-set) | known classes only; arm A |
| Per-class recall | every known family and each held-out family; Bot and WebAttack are always shown, not only averaged |
| Unknown recall at fixed FPR | (i) **conformal**: at α ∈ {0.1, 1, 5} %, with the *realised* FPR shown beside it; (ii) **oracle-threshold**: at exactly 1 % FPR set on test benign — labelled "oracle", for threshold-free comparison with CLOSR only |
| AUROC-OOD / AUPR-OOD | benign vs unknown (primary); known-attack vs unknown (open-set separation); AUPR at the natural test prevalence, stated |
| FPR | realised benign FPR vs nominal α; max \|FPR − α\| over the three α |
| Calibration | (a) conformal validity: realised FPR vs α curve; (b) ECE (15 bins) and Brier score of the closed-set class probabilities on test known classes |
| Cross-dataset generalisation | P3/P4: all of the above, plus Δ to the source IID record of the same seed |
| Temporal generalisation | P2: same, Mon–Wed→Thu and Mon–Thu→Fri |
| Recalibration effect | for each W: ΔFPR and Δrecall vs no adaptation; **known and unknown recall at matched realised FPR** (the R1b finding) |
| Latency | per-flow inference time at batch 1 (median and p99 over 10,000 calls) and throughput at batch 10,000; fit time |
| Memory | peak RSS during fit and inference (`psutil`, sampled at 10 Hz); serialised model size |

---

## 11. Statistics

* **Unit of analysis = seed.** Folds (LOAFO), days (P4) and windows are averaged within a seed first.
* **Confirmatory comparisons are pre-registered** (listed below):
  * two-sided paired t-test over seeds (primary) and Wilcoxon signed-rank (sensitivity);
  * **Holm correction** within each hypothesis family;
  * 95 % Student-t CIs of the paired difference; effect size = mean difference.
* **"No worse" claims** use equivalence testing (TOST) with a pre-set margin of ±0.02 recall. Absence of significance is never reported as equivalence.
* **Per-family and rare-class metrics** get bootstrap CIs over flows within a record (2,000 resamples) and are descriptive. Fold-level win counts are descriptive only, as in the paper.
* **Exploratory results** (everything not in the list below) are labelled exploratory, with no p-value-based claims.

**Pre-registered hypotheses.**

| ID | Hypothesis | Supported if | Rejected if |
|---|---|---|---|
| R3-H1 | Pipeline gain generalises across evidence models: for each tunable supervised m, arm C (Fisher) > arm B in LOAFO zero-day recall at α = 1 % | ≥ 6 of 8 models show a positive mean difference with Holm-adjusted p < 0.05 | ≤ 3 of 8 do; then the LOAFO gain is reported as XGB-specific |
| R3-H2 | Choice of evidence model matters: the best arm-C model differs from arm-C XGB by ≥ 0.03 zero-day recall (either direction) | Holm-adjusted p < 0.05 and \|Δ\| ≥ 0.03 | TOST shows equivalence within ±0.02 |
| R3-H3 | CLOSR vs Aegis-OSR(XGB) at α = 1 % in LOAFO, arm B (CLOSR OOD score) vs arm C (XGB) | No direction pre-committed: report Δ with CI | — |
| R3-H4 | Validity: realised FPR at α = 1 % under LOAFO lies in [0.8, 1.2] % (seed mean) for every model in arms B and C | all models | any model fails → calibration bug, stop and fix before any other result is read |
| R3-H5 (robustness, discovery data) | Under P4 recal@2000, Fisher-fused arm C known recall < arm B known recall for each supervised m | ≥ 6 of 8 models | ≤ 3 of 8 — the inversion is then XGB-specific |

---

## 12. Reproducibility and artifact preservation

1. **Regression gate before any R3 run.** Arm C with XGB (reference configuration) must reproduce `openset_loafo_records.json` for seeds 1–5 exactly (all 1,320 values, as in R1b's reproduction check). If it does not, stop.
2. **Separate outputs.** `research_artifacts/r3/{loafo,temporal,cross,perday}_records.json`, summaries, `r3_manifest.json`. Nothing under the existing `openset_*` names is written. A test asserts that the existing artifacts' hashes are unchanged after R3.
3. **Record metadata:**
   * git commit, `requirements-r3.txt` hash, package versions, CPU model, thread count;
   * seeds, split hashes (row-hash digests), the tuned configuration per (model, fold);
   * wall-clock times, peak RSS.
4. **Configurations.** Tuning studies are saved as Optuna SQLite (`research_artifacts/r3/tuning/`, git-ignored) and the chosen configurations as committed JSON.
5. **Dumps and models.** Score dumps are kept as in §8.4. Model files are kept for seed 101 only.
6. **Publication.** Tables enter the paper only through `research/publication.py` builders, as in R1b.

---

## 13. Execution stages, acceptance and failure criteria

| Stage | Content | Needs approval for | Acceptance | On failure |
|---|---|---|---|---|
| **0** | Install pinned packages into the main env (LightGBM, CatBoost, TabM, Optuna) and `.venv-closr`; download LycoS-IDS2017 (if licence allows) and the CLOSR repo; **pilots**: 1 fit of each model on seed 0 / LOAFO-DoS to measure time and RAM; TabICL CPU pilot | installs, dataset download, pilot runs | the measured times replace §2 estimates; the R3 plan fits in ≤ 10 days of wall-clock | drop or reduce the costliest arm (TabM S = 5 / CLOSR option 3); report the change |
| **0-TabICL** | context ≤ 50 k stratified training rows, predict 10 k rows, `device="cpu"`, `n_jobs=14`, pinned checkpoint | same | fit + predict ≤ 10 min, peak RAM ≤ 16 GB, and the full protocol extrapolates to ≤ 48 CPU-h | TabICL stays in reserve; reason recorded |
| **1** | CLOSR reproduction (1a, 1b) | — | §8.3 tolerances | reported as a reproduction failure; Stage 2 uses the best faithful configuration |
| **R** | Regression gate (§12.1) | — | 1,320/1,320 identical | stop |
| **2** | Tuning (§7), then confirmatory runs P1–P4 | — | all leakage checks pass; R3-H4 validity holds | invalid records rerun; validity failure stops the study |
| **3** | Analysis: pre-registered tests, then exploratory | — | — | — |

**Study-level failure criteria** (any one stops interpretation until resolved):
* the regression gate fails;
* any leakage check fails;
* R3-H4 fails for the reference XGB;
* existing artifact hashes change.

**What R3 may conclude.**
* Which evidence models work at a calibrated operating point, and at what cost.
* Whether Aegis-OSR's gain and its cross-network failure are model-specific.
* How CLOSR compares under our protocols.

**What it may not conclude.**
* That any method detects zero-days in general.
* That the FPR bound holds under shift.
* Anything from P4 as confirmation of the fusion mechanism. P4 is the discovery data; confirmation belongs to the Contribution-1 protocol on new targets.

---

## 14. Stage 0 amendments (2026-11-17, proposed for approval)

Stage 0 produced the following changes. Each is backed by a measurement or finding recorded in `R3_ENVIRONMENT.md`, `CLOSR_PILOT_REPORT.md`, `DATASET_LICENCE_CHECK.md` or `CLAIM_AUDIT.md` §10.

| # | Change | Reason |
|---|---|---|
| A1 | **De-duplicate at float32 precision before any split** (`research/data.dedup_float32`). The historical protocols keep the original behaviour, so the regression gate still reproduces them exactly. | `_finalize` de-duplicates before the float32 cast. 22,818 CICIDS2017 rows (0.9 %, nearly all benign) and 18,839 CSE-CIC-IDS2018 rows are exact float32 duplicates and can fall on both sides of a split. The R3 leakage check caught this on its first smoke run. |
| A2 | **Two isolated environments.** `.venvs/r3-cpu` for trees/GBDT and the gate; `.venvs/r3-cuda` (torch 2.12.0+cu126) for CLOSR and TabM. Every torch model pins its device explicitly. | CPU cost for CLOSR is ≈ 19 h per fit and for TabM ≈ 10 h. The GPU brings these to 1.3 h and 0.3 h, using < 2 GB VRAM. |
| A3 | **CPU/GPU agreement check** on one seed before any GPU campaign, with a tolerance fixed in advance: \|Δ zero-day recall\| ≤ 0.01. | GPU kernels are not bit-identical to CPU. |
| A4 | **CLOSR Stage 1a/1b is blocked** until LycoS-IDS2017 is approved. Use the official Le Mans source, not the Google Drive copy. Any reproduction writes checkpoints outside the clone. | Licence check; `train_closr.py` overwrites the released weights. |
| A5 | **CLOSR in Stage 2:** 200 epochs as published (no early stopping), 5 seeds (101–105), LOAFO + per-day only ≈ 46 GPU-h. 10 seeds (≈ 93 GPU-h) only if the user approves the budget. | Measured 1.3 GPU-h per fit. |
| A6 | **TabM:** GPU, official defaults plus §7 tuning on a 200 k subsample. Before tuning, one full fit measures the real number of epochs to early stopping. | The 30-epoch figure is an assumption. |
| A7 | **Seeds.** Confirmatory runs use 101–110, with pilot seed 0 only. Smoke and timing runs use seed 0 and are never reported. | Unchanged from §6; now enforced by the runner. |
| A8 | **Arm A (native argmax)** is computed from the score dumps (`pred_class_idx`). It is not added to the records. | Keeps the historical record format, so the gate can compare exactly. |
| A9 | **Cross-dataset feature-identical rows** (2017 train vs 2018 test) are logged as informational, not as leakage. Within one dataset (warm-up vs evaluation, train/val/test) any overlap is fatal. | They are different captures. |
| A10 | **At most two concurrent data-loading jobs** on this machine. | Each job holds 4–6 GB RSS. Running the gate, a smoke test and two pilots together caused swapping (one gate seed took 16× longer). |
| A11 | **Confirmation targets for Contribution 1:** NF-v3 pairs (shared NetFlow schema, millisecond timestamps). LycoS-Unicas-IDS2018 is unsuitable for per-day work: one file, subsampled benign, timestamps unconfirmed. There is no NF-v3 version of CICIDS2017. | Licence and structure check. |
| A12 | **Runner safety.** `scripts/67_r3_run.py --campaign` refuses to start without `--i-have-approval`. Outputs go only to `research_artifacts/r3/`, and protected paths are refused. | The user's Stage 0 restrictions. |
