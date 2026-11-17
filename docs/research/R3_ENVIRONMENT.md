# R3 environments and CUDA feasibility (Stage 0, 2026-11-17)

## 1. Principle

* The **main project environment is untouched.** It has no LightGBM, CatBoost, Optuna or TabM, and `requirements*.txt` are unchanged.
* R3 runs in two isolated virtual environments under `.venvs/` (git-ignored). Both use the system Python 3.11.9.
* The two environments differ in exactly one package, the torch build. Their freezes are compared in §2.

| Env | Purpose | torch | Freeze |
|---|---|---|---|
| `.venvs/r3-cpu` | Tree / GBDT models, regression gate, smoke tests | 2.12.0+cpu (same version as the main env) | `docs/research/envs/freeze-r3-cpu.txt` |
| `.venvs/r3-cuda` | CLOSR and TabM | 2.12.0+cu126 | `docs/research/envs/freeze-r3-cuda.txt` |

**Pins.** `docs/research/envs/requirements-r3-common.txt`:
* identical to the main environment: numpy 2.4.2, pandas 2.3.3, scipy 1.17.1, scikit-learn 1.9.0, xgboost 3.2.0, pyarrow 24.0.0, joblib 1.5.3;
* R3 additions: lightgbm 4.7.0, catboost 1.2.10, optuna 5.0.0, tabm 0.0.3, rtdl_num_embeddings 0.0.12, psutil.

**Recreating an environment:**

```
python -m venv .venvs/r3-cpu
.venvs/r3-cpu/Scripts/python -m pip install torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu
.venvs/r3-cpu/Scripts/python -m pip install -r docs/research/envs/requirements-r3-common.txt
```

For r3-cuda, use `--index-url https://download.pytorch.org/whl/cu126` instead.

## 2. Verification

* **Packages.** All R3 packages import in `r3-cpu` at the pinned versions. Apart from the torch build, the r3-cpu and r3-cuda freezes are identical.
* **Smoke test.** The R3 runner smoke test passes in `r3-cpu` for all seven tree/GBDT models (DT, RF, Extra Trees, XGBoost reference, XGBoost tuned-capable, LightGBM, CatBoost). It covers the LOAFO and per-day protocols, with:
  * leakage checks on 28 splits (all pass);
  * per-flow dumps written for every record and variant.

## 3. CUDA feasibility

| Item | Finding |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8,188 MiB, compute capability 8.9 (Ada) |
| Driver | 560.94 (WDDM), supports CUDA ≤ 12.6 |
| PyTorch builds | cu126 wheels exist for torch 2.12.0 (chosen: the same version as the CPU env). The cu128 builds need driver ≥ 570, so they are not usable without a driver update |
| Installed | torch 2.12.0+cu126, cuDNN 9.10.2. `torch.cuda.is_available()` is True, and a 4096×4096 matmul succeeds |
| Download / disk | The torch cu126 wheel is 2.62 GB. 109 GB free on D: |

**Measured on small workloads** (pilot seed 0, CICIDS2017; JSON in `research_artifacts/r3/pilots/`):

| Model | Device | Batch | Time per step | Peak VRAM | Peak RSS | Extrapolated cost of one fit at R3 size (~600 k rows) |
|---|---|---|---|---|---|---|
| CLOSR (official code, paper defaults) | GPU | 4,096 | 0.163 s | 1.8 GB | 4.7 GB | 24 s/epoch → **1.3 h** for 200 epochs |
| CLOSR | CPU (20 threads)* | 4,096 | 2.3 s | — | 6.3 GB | 5.6 min/epoch → **≈19 h** for 200 epochs |
| TabM (k = 32, PLE embeddings, official defaults) | GPU | 1,024 | 0.062 s | 1.0 GB | 3.9 GB | 36 s/epoch → **0.3 h** at 30 epochs (assumed) |
| TabM | CPU* | 1,024 | 2.0 s | — | 4.2 GB | 19 min/epoch → **≈10 h** at 30 epochs |

\*The CPU runs were measured while the regression gate was using the CPU, so they may be pessimistic. They are 14–32× slower than the GPU, so the conclusion (CPU not viable for CLOSR or TabM) does not depend on the contention.

**Verdict.**
* The GPU route is feasible for CLOSR and TabM. Both use under 2 GB of VRAM at the paper's batch sizes, so there is headroom for 2 parallel jobs.
* CPU-only CLOSR or TabM is not feasible for the full protocol.

**Still to check before any GPU campaign:**
1. CPU/GPU agreement on one seed. Results will differ slightly, because GPU kernels are not bit-identical; the agreement tolerance must be set in advance.
2. Thermal throttling on a laptop over multi-hour runs.
3. `torch.use_deterministic_algorithms(True)` on CUDA, which may need `CUBLAS_WORKSPACE_CONFIG=:4096:8`.

## 4. Not done

* The CLOSR repository's own pins (torch 2.0.1, numpy 1.24.2, pandas 2.0.0, scikit-learn 1.2.2) were **not** installed. That environment is only meaningful for the faithful reproduction on LycoS-IDS2017 (Stage 1b), which waits on dataset approval. torch 2.0.1 has a cu118 build that this driver supports.
* TabICL: not installed (deferred).
