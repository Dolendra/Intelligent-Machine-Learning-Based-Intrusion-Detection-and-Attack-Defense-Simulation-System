# CLOSR pilot reproduction report (R3 Stage 0, 2026-11-17)

**Scope.** This is an execution, faithfulness and cost pilot. It is **not** a reproduction of the published numbers: those require LycoS-IDS2017, whose download is not yet approved (see `DATASET_LICENCE_CHECK.md`).

**Code.** github.com/jackwilkie/CLOSR @ `79da4d1f2a6f4e5ecf92c4588195aaf163df40f8` (Apache-2.0), cloned into a scratch directory. It is not vendored into this repository.

**Pilot script.** `scripts/66_closr_pilot.py`. Results are in `research_artifacts/r3/pilots/closr_*.json`.

## 1. Does the official implementation run?

| Question | Answer |
|---|---|
| Do CLOSR's modules (model, loss, balanced sampler, LR schedule, `closr_eval`) run unmodified? | **Yes**, in our isolated envs: torch 2.12.0 on CPU and on CUDA 12.6 (RTX 4060). The loss decreases (0.371 → 0.333 over 2 pilot epochs) and the official evaluation function completes. |
| Do the official entry scripts (`train_closr.py`, `eval_closr.py`) run on our data unmodified? | **No.** `d_in=72` is hard-coded and the scripts expect `data/lycos.csv` with LycoS column names. They can only run unmodified on LycoS data. |
| Do they run under the repository's own pins (torch 2.0.1, numpy 1.24.2, pandas 2.0.0, scikit-learn 1.2.2)? | **Not tested.** Those pins matter only for the faithful reproduction (Stage 1b), which waits on the LycoS approval. |
| Does running `train_closr.py` as published have side effects? | **Yes.** It saves to `weights/closr.pt.tar` and **overwrites the released pretrained weights**. Any reproduction must write elsewhere; the pilot writes no checkpoint. |

## 2. Is the paper's methodology faithfully implemented? Paper vs. released code

| # | Item | Paper | Code (`79da4d1`) | Consequence |
|---|---|---|---|---|
| 1 | CLOSR loss over classes | Sum over classes (Eqs. 11–12) | **Mean** over classes (`losses/closr_loss.py`) | Scale only; equivalent to a learning-rate change |
| 2 | Pair normalisation | Per anchor (Eq. 7) | By the count of non-zero pair terms across the batch, with an α = 0.5 split between similar and dissimilar terms and a `relu(m − d)` hinge | Matches the paper's form at m = 1, up to normalisation |
| 3 | Zero-day classes | "Web Attack (SQL Injections) and Heartbleed" | Every class with fewer than `sample_thres = 100` flows (`data/load_data.py`) | The two coincide only if no other LycoS class has < 100 flows (to be confirmed on the data) |
| 4 | Feature selection | Not described | All-zero columns dropped using the **whole file** before the split | Label-free, so no label leakage, but test rows influence preprocessing; we decide on the training split only |
| 5 | Seeds / repeats | "20 training and evaluation runs" | **No seed is set anywhere**; there is no 20-run driver and no Wilcoxon code | Runs are not reproducible bit-for-bit; we set seeds |
| 6 | Arguments | — | `--residual` and `--squared` are `type=bool`, so any given value parses as True | Only matters if the flags are passed |
| 7 | Label alignment | — | `y` taken from the frame **before** `dropna()`, `X` after | Silent misalignment if the CSV has NaN rows |
| 8 | Threshold | "not calibrated in this work" | None | Only threshold-free metrics are reported |
| 9 | OpenAUC | Cites Wang et al. | Closed-set accuracy × open-set AUROC | A simplification of the pairwise OpenAUC |
| 10 | **AUROC direction** | — | **CLAD** per-class AUROC (`eval_clad.py` → `balanced_auroc` → `mean_auroc`) returns `max(roc, 1 − roc)` per class. The score passed in is the *similarity to the benign centroid*, which is higher for benign, so the flip also acts as the sign convention. **CLOSR**'s open-set AUROC (`eval_closr.py`) is a plain `roc_auc_score(ood, −osr_score)` with no flip. | Paper Table I's CLAD zero-day AUROC (0.9966) uses label-dependent direction selection; Table III's CLOSR open-set AUROC (0.9740) does not. A class that ranks *worse* than chance is reported as better than chance. Whether this changes any published number can only be checked on LycoS. |

## 3. Data and split requirements (for Stage 1b)

**Data.** LycoS-IDS2017 per-day CSVs, merged into one `lycos.csv`. No merge script is provided.
* The README alternatively links a Google Drive "preprocessed version" with no stated redistribution authorisation, so **use the official source**.
* Labels must be lower-case with `benign` as class zero.
* Dropped columns: `flow_id, src_addr, src_port, dst_addr, dst_port, ip_prot, timestamp`.

**Split.**
* Single stratified 50/50 split with `split_seed = 39058032`.
* Zero-day = classes with < 100 flows.
* z-normalisation on the training half.

**Released weights.** `weights/closr.pt.tar` (35.6 MB) and `weights/clad.pt.tar` (38.8 MB). They were trained on that exact split, so they can be used **only** for Stage 1a, which evaluates them on the authors' own split. They cannot be used on our protocols.

## 4. Computational requirements (measured)

| Setting | Time per step (batch 4,096) | Epoch at 600 k rows (R3) | One 200-epoch fit | Peak memory |
|---|---|---|---|---|
| GPU (RTX 4060, torch 2.12 + cu126) | 0.163 s | 24 s | **1.3 h** | 1.8 GB VRAM, 4.7 GB RSS |
| CPU (20 threads, under contention) | 2.3 s | 5.6 min | ≈ 19 h | 6.3 GB RSS |

At paper scale (≈ 895 k training rows, about 218 steps per epoch), one run is about 2 GPU-hours:
* the paper's 20 runs would take ≈ 40 GPU-h;
* our Stage 1b plan of 3 runs takes ≈ 6 GPU-h.

## 5. Our independent, leakage-free evaluation of CLOSR

Two evaluations are kept strictly separate.

**Reproduction.** Report the authors' metrics exactly as their code computes them, including `max(roc, 1 − roc)`, and label them as such.

**Independent comparison** (R3 Stage 2). The direction is fixed in advance and never chosen from labels:
* **CLOSR unknown score:** s = Σ_c P(c|x)·(h_c(z)·μ_c)², negated (Eq. 16; as in `eval_closr.py`).
* **CLAD score:** the negative similarity to the benign centroid.
* **Operating point:** set by the same split-conformal calibration on benign data as every other method, never by a threshold tuned on test labels.

A test asserts that the evaluation code contains no `max(roc, 1 − roc)`.

## 6. Recommendation

* **Stage 1a** (evaluate the released weights): about 1 GPU-hour, once LycoS is approved.
* **Stage 1b** (3 seeded re-trainings): ≈ 6 GPU-h.
* **Stage 2** (CLOSR under our protocols): 1.3 GPU-h per fit. That is 46 GPU-h at 5 seeds (35 fits) or 93 GPU-h at 10 seeds (70 fits), both for LOAFO + per-day.

The previous CPU estimate of 180–360 h is replaced: CPU is infeasible (about 19 h per fit), and GPU is feasible.
