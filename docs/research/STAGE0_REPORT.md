# R3 Stage 0 checkpoint report (2026-11-17)

**Branch:** `v3-openset-research`. All commits are local; nothing pushed or merged. `main` and `v1.1-research` are untouched.

**Scope.** No R3 campaign was run. Everything below is inspection, installation in isolated environments, small pilots, the regression gate and readiness checks.

**Status labels used here:**
* **reproduced** — an existing result was re-obtained exactly;
* **new finding** — measured in Stage 0;
* **hypothesis** — not yet tested.

## 1. Environment and dependencies → `R3_ENVIRONMENT.md`

* **Main environment untouched.** It has none of the R3 packages, and the requirement files are unchanged.
* **`.venvs/r3-cpu` and `.venvs/r3-cuda`.** Both use the main environment's exact versions of numpy, pandas, scipy, scikit-learn, xgboost and pyarrow, plus:
  * lightgbm 4.7.0, catboost 1.2.10;
  * optuna 5.0.0 (5.1.0 was released the day before, so it was not used);
  * tabm 0.0.3 and rtdl_num_embeddings 0.0.12.

  The only difference between the two is the torch build: 2.12.0+cpu vs 2.12.0+cu126. Pins and freezes are in `docs/research/envs/`.
* **The isolated environment reproduces the historical results exactly** (§4, re-gate).

## 2. CUDA feasibility → `R3_ENVIRONMENT.md` §3

* **Hardware.** RTX 4060 Laptop GPU, 8 GB, compute capability 8.9. Driver 560.94 supports CUDA ≤ 12.6, so cu126 wheels work; cu128 would need a driver update. `torch.cuda` is available.

| Model | GPU (per fit at R3 size) | CPU | VRAM |
|---|---|---|---|
| CLOSR (official modules, batch 4,096, 200 epochs) | **1.3 h** | ≈ 19 h | 1.8 GB |
| TabM (k = 32, PLE, batch 1,024, 30 epochs assumed) | **0.3 h** | ≈ 5.8 h (uncontended) | 1.0 GB |

* **Verdict.** The GPU is necessary for CLOSR and TabM, and feasible. The CPU environment was left untouched.
* **Before any GPU campaign:**
  * a CPU/GPU agreement check on one seed (tolerance \|Δ recall\| ≤ 0.01, fixed in advance);
  * a thermal check on long runs.

## 3. CLOSR pilot reproduction → `CLOSR_PILOT_REPORT.md`

**Does the code run?**
* The official modules run unmodified on CPU and GPU with torch 2.12, and the loss decreases.
* The entry scripts cannot run on our data: `d_in = 72` is hard-coded and they expect the LycoS file.
* The repository's own pins (torch 2.0.1 etc.) were not tested; that test belongs to Stage 1b.

**Side effect.** `train_closr.py` **overwrites the released pretrained weights**. Any reproduction must write elsewhere.

**Ten paper/code differences are documented.** The important ones:
* No seeds are set anywhere.
* Zero-day classes are chosen by count (< 100 flows).
* `y` is aligned before `dropna()` while `X` is taken after.
* **AUROC direction.** CLAD's per-class AUROC uses `max(roc, 1 − roc)`, which affects paper Table I (zero-day 0.9966). CLOSR's own open-set AUROC (Table III) does not use it.

Our independent evaluation fixes the score direction in advance. A test enforces that no `max(roc, 1 − roc)` appears in our code.

**Data.**
* The faithful reproduction needs LycoS-IDS2017 from the official Le Mans source, plus the authors' split seed `39058032`.
* The released weights are valid only on that split.

**The published numbers were not reproduced**, because the dataset is not approved.

## 4. Regression gate → `research_artifacts/r3/regression_gate_report*.json` — **PASS**

| Check | Full gate (main env, code `bf5fd3f`) | Re-gate (isolated `r3-cpu`, code `3a0450e`, seed 1) |
|---|---|---|
| Historical artifacts unchanged (25, SHA-256) | pass | pass |
| Frozen v1.1 files identical to tag (16) | pass | pass |
| Frozen v1.1 re-score on 2018 v2 | reproduces | (skipped) |
| LOAFO exact reproduction with score dumps | 30 records, **6,690/6,690 values identical** | 6 records, identical |
| Per-day exact reproduction with score dumps | 50 records, **61,730/61,730 identical** | 10 records, identical |
| Every evaluated flow has evidence-stream scores | 380 dumps, 15,327,730 flows | pass |
| New experiments cannot overwrite results | refused | refused |

**Gate assets.** `research/artifact_guard.py` (manifest, `assert_writable`), `research/scoredump.py`, `scripts/65_regression_gate.py`, `tests/test_artifact_integrity.py`.

## 5. LOAFO and per-day readiness → `scripts/67_r3_run.py`

**Model registry** (`research/r3_models.py`):
* DT, RF, Extra Trees, XGBoost-reference (exact v3 configuration), XGBoost, LightGBM, CatBoost.
* Early stopping uses a 10 % split carved from training only.
* Search spaces follow R3_PROTOCOL §7.

**Arms.**
* **B and C:** each model standalone ("sup only") and inside Aegis-OSR (Fisher, max, omnibus) through the same conformal calibration.
* **A (native):** from the dumps.

**Built-in controls:**
* leakage checks on every split;
* per-flow dumps;
* float32 de-duplication before splitting (§6 finding);
* guarded outputs;
* fixed seeds (confirmatory 101–110; pilot 0);
* `--campaign` refuses without explicit approval.

**Smoke test** (all 7 models × LOAFO + per-day, tiny caps): pass, 28 splits leak-free.

**Timing pilot** (one full-size LOAFO fold, seed 0): pass, 7 splits leak-free.

| Model | Fit (s) | Wall per record (s) | Score (ms / 1k flows) | Peak RSS (GB) |
|---|---|---|---|---|
| XGB reference (with all v3 baselines) | 56.4 | 74 | 47 | 5.5 |
| Decision Tree | 10.3 | 22 | 30 | 4.3 |
| Random Forest (300) | 33.4 | 46 | 35 | 4.4 |
| Extra Trees (300) | 19.1 | 32 | 37 | 4.4 |
| XGBoost (early stopping) | 11.8 | 24 | 33 | 4.4 |
| LightGBM (early stopping) | 14.9 | 35 | 67 | 4.4 |
| CatBoost (early stopping) | 231.4 | 244 | 31 | 4.4 |

The timing ran after more than 3 hours of full CPU load on a laptop, so there may be thermal throttling (one re-gate seed ran ~3× slower than earlier). Treat these as upper-end estimates.

## 6. New finding: float32 duplicates (CLAIM_AUDIT §10.2)

**What the leakage checker caught.** About 0.9 % of CICIDS2017 rows (22,818; almost all benign) are exact duplicates at the float32 precision the models use. The cause: data preparation de-duplicates *before* casting to float32.

**Overlap in the historical splits:**
* LOAFO: 0.31 % of test benign rows have a twin in training, and 0.064 % in the calibration source.
* Per-day: up to 0.86 % on 2018-02-28; ≤ 2 rows on the other days.

**Impact.** The maximum effect on any realized FPR is ≤ 0.31 points (LOAFO) and ≤ 0.86 points on one near-chance day. No conclusion changes. The committed numbers are kept, with this note.

**Fix.** R3 de-duplicates first.

## 7. Dataset licence verification → `DATASET_LICENCE_CHECK.md` (nothing downloaded)

| Dataset | Licence | Redistribution | Timestamps | Fit |
|---|---|---|---|---|
| LycoS-IDS2017 (official: lycos-ids.univ-lemans.fr, ≈ 532 MB zip) | none stated; "available for researchers", cite | not stated → commit code/metrics only | yes (µs, per day) | CLOSR reproduction; Contribution 2 |
| LycoS-Unicas-IDS2018 (GitHub README → Google Drive) | none stated; cite | not stated (parent CIC-2018 permits with citation) | unconfirmed; benign subsampled to 10 M | Contribution 2 (not per-day) |
| NF-v3 (UQ; 4 sets, 2.4–27.5 M flows) | none stated; cite | not stated | yes (ms) | Contribution 1 confirmation (no CICIDS2017 member) |

**The CLOSR repo's Google Drive copy of LycoS has no stated redistribution authorisation.** Do not use it.

## 8. Updated cost estimate (replaces R3_PROTOCOL §2.2)

| Block | Seeds | Estimate | Device |
|---|---|---|---|
| CPU models, library defaults, LOAFO + per-day (7 models) | 10 | ≈ 11–12 h wall (fit 7.3 h, plus evaluation and per-day adaptation). CatBoost alone is ≈ 5 h | CPU, ≤ 2 parallel jobs |
| Tuning, 30 TPE trials × 7 tuning tasks on a 200 k subsample (6 CPU models) | — | ≈ 19 CPU-h (CatBoost ≈ 13.5 h of that) | CPU |
| TabM (defaults + tuning) | 10 | ≈ 21 GPU-h + ≈ 21 GPU-h | GPU |
| CLOSR Stage 2 (200 epochs) | 5 / 10 | ≈ 46 / 93 GPU-h | GPU |
| CLOSR Stage 1a / 1b (needs LycoS) | — / 3 | ≈ 1 / 6 GPU-h | GPU |
| Score dumps | — | ≈ 20 GB (109 GB free) | — |

**Total.**
* **CPU part:** about 1.5–2 days of wall time.
* **GPU part:** 90–160 GPU-hours, i.e. 4–7 days of continuous laptop GPU time, depending on CLOSR seeds and TabM tuning.

## 9. Changes to the R3 protocol → `R3_PROTOCOL.md` §14 (A1–A12)

The main changes:
* float32 de-duplication before splitting;
* isolated CPU/GPU environments and a CPU/GPU agreement check;
* CLOSR Stage 1 blocked on LycoS approval;
* CLOSR at 5 seeds unless a larger GPU budget is approved;
* TabM epochs measured before tuning;
* arm A computed from the dumps;
* cross-dataset twins treated as informational;
* at most 2 concurrent data jobs;
* NF-v3 as the Contribution 1 confirmation target.

## 10. Paper wording (approved) — done (`2336945`, CLAIM_AUDIT §9.3)

"Undetectable" now applies only to the frozen detector at its fixed thresholds, and the recalibrated-classifier evidence is labelled exploratory.

**One related sentence was flagged, not changed:** "cannot create separation the evidence lacks", in both papers. It needs your decision.

## Decisions requested

1. Approve the R3 protocol amendments A1–A12.
2. Approve the CPU campaign: 7 models, defaults + tuning, LOAFO + per-day, seeds 101–110 (≈ 1.5–2 days).
3. GPU: approve the CPU/GPU agreement check plus the TabM campaign (≈ 42 GPU-h) and CLOSR at 5 seeds (≈ 46 GPU-h), or a smaller budget.
4. Datasets: approve downloading LycoS-IDS2017 (official source; commit code and metrics only). This unblocks CLOSR Stage 1. NF-v3 can follow when Contribution 1 confirmation starts.
5. Decide on the flagged sentence "cannot create separation the evidence lacks".
