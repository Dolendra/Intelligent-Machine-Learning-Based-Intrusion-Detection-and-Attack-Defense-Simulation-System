# Full repository audit (Phase 0): consolidated report

**Date:** 2026-11-18. **Type:** read-only audit. No application code, models, datasets or experiment results were changed.
**Audit branch:** `audit/full-repository-2026-11`, created locally from `v3-openset-research` @ `440dec4`. It contains only these audit documents and has not been pushed.

**Companion documents:**

| Document | Content |
|---|---|
| `SECURITY_AUDIT.md` | SEC-1 … SEC-29, route/auth table |
| `ML_PIPELINE_AUDIT.md` | ML-1 … ML-23 (production ML), RES-1 … RES-22 (research methodology) |
| `ARCHITECTURE_AUDIT.md` | ARCH-1 … ARCH-30, frontend↔backend contract |
| `RESEARCH_ALIGNMENT_REVIEW.md` | answers to the 7 research questions, alignment verdict |
| `docs/roadmap/` | PROJECT_STATUS, ARCHITECTURE_STATUS, IMPLEMENTATION_GAPS, MASTER_ROADMAP, REMEDIATION_PLAN |

**What passing checks do not show:** the build and tests pass, but that does not show the code is secure or the research correct. Several High findings below sit on paths that the passing tests do not exercise.

---

## 1. Audit scope verification

### 1.1 Branches and exact commits audited

| Branch | Local SHA | `origin` SHA | Last commit | Role |
|---|---|---|---|---|
| `main` | `775e9a9c6de8925b43b36ef1dd5d3389fa143427` | identical | 2026-09-15 | Stable application, v2.0 productionized, plus the final report and viva pack |
| `productionization` | `76da1037834b26d7d7e220d65c195f75fe7a242b` | identical | 2026-09-15 | P1–P12 productionization; **fully merged into main** (PR #2) |
| `stage2/productionization` | `63871c0daa57c1ece0dc7ca9f51d68b746902c59` | identical | 2026-09-14 | Stage-2 hardening; **fully merged into main** (PR #1, which became tag `v1.1-research`) |
| `v3-openset-research` | `440dec4c23a24e48c79b8e01f851a4984cedc26b` | identical | 2026-11-17 | Research: Aegis-OSR, R1a–R3 Stage 0, UI redesign |

**Topology.** Each branch fully contains the one before it:

```
stage2/productionization ⊂ productionization ⊂ main ⊂ v3-openset-research
```

| Pair | Ahead | Behind |
|---|---|---|
| `productionization` vs `main` | 0 | 7 |
| `stage2/productionization` vs `main` | 0 | 23 |
| `v3-openset-research` vs `main` | 17 | 0 |

There are no divergent or conflicting implementations between branches. Every older branch is an ancestor of the newer ones.

### 1.2 Frozen baseline

Tag `v1.1-research` points to commit `b1a8157`. The 16 frozen v1.1 files (`research/artifact_guard.py: FROZEN_V11`) were checked with `git diff --quiet v1.1-research <branch> -- <16 files>` on each branch:

| Branch | Frozen files identical to tag |
|---|---|
| `main` | **True** |
| `productionization` | **True** |
| `stage2/productionization` | **True** |
| `v3-openset-research` | **True** |

The 25 research artifacts protected by SHA-256 also pass: `verify_manifest()` returned `{}` and `frozen_v11_diff()` returned `[]`.

### 1.3 Isolation

| Step | Where it ran | Repository state afterwards |
|---|---|---|
| Audit work | Local branch `audit/full-repository-2026-11` (no upstream) | `git status --porcelain` empty until the audit documents were written |
| `main` tests | Detached scratch worktree at `775e9a9`, outside the repo | — |
| Probes | Scratch DBs and scratch temp dirs, `PYTHONDONTWRITEBYTECODE=1` | — |
| After every test and probe run | — | Clean |

### 1.4 Branch content summary

| | `main` | `v3-openset-research` |
|---|---|---|
| Tracked files | 352 | 707 (406 changed relative to main) |

**What v3 adds:**
* `research/` (15 modules)
* `scripts/50–69`
* `research_artifacts/`
* research documents and papers
* `cyberrange/`
* a frontend redesign (60 files added, 23 modified)

**What v3 modifies in application code:** 22 files, +1,158/−42 lines.
* `backend/services/pipeline.py`: Zero-Day Gate and detection policy
* `backend/routes/{v3,range}.py`: new routes
* `backend/services/live_stream.py`: new file
* `api_auth.py`: RBAC prefixes for the new routes
* `security/{detection_policy,threat_intel}.py`: new files
* `config.yaml`: `zero_day_gate.incident_policy: union`

**Which branch is which:**
* Stable application: `main`.
* Research: `v3-openset-research`.
* `productionization` and `stage2/productionization` are historical. They are **not recommended for deletion** without explicit approval.

## 2. Validation run log

Every command below was actually executed. None was skipped silently.

| # | Command | Environment | Result |
|---|---|---|---|
| 1 | `MPLBACKEND=Agg DISABLE_RATE_LIMIT=true python -m pytest tests -q -rs -p no:cacheprovider` (CI settings) | system Python 3.11.9, research branch | **297 passed**, 0 failed, 0 skipped, 1 warning (66 s) |
| 2 | Same as #1 | detached worktree of `main` @ 775e9a9 | **213 passed**, 1 warning (21 s) |
| 3 | `pytest tests/test_productionization_p4_auth.py …p5_security.py tests/test_phase_c_security.py tests/test_phase_d_hardening.py tests/test_productionization_p6_persistence.py` **without** `DISABLE_RATE_LIMIT` | research branch | **48 passed** |
| 4 | `npm run typecheck` (`tsc --noEmit`) | Node 22.13.1, research branch | **pass** (exit 0) |
| 5 | `npm test` (`vitest run`) | research branch | **12 files, 49 tests passed** |
| 6 | `npx vite build --outDir <scratch>` | research branch | **pass** (built in 4.0 s) |
| 7 | `alembic upgrade head`, then `alembic check`, `alembic downgrade base`, `alembic upgrade head` | throwaway SQLite DB (`IDS_DB_URL`) | **pass**; `check`: "No new upgrade operations detected" |
| 8 | `python -m compileall` over all Python packages | research branch | **pass** (exit 0) |
| 9 | `research.artifact_guard.verify_manifest()` / `frozen_v11_diff()` | research branch | `{}` / `[]`, no differences |
| 10 | Frozen-file diff against the tag on 4 branches (§1.2) | git | identical on all four |
| 11 | Secret scan: secret regexes over the 4 branch tips; filenames ever added in history | git | **clean** (one test fixture string `"should-not-appear"`) |
| 12 | Research regression gate (full retraining, `scripts/65`) | — | **Not re-run.** Its last run passed: full gate at `bf5fd3f`; r3-cpu re-gate at `3a0450e`. Since then the only code change is the 6-line `--tag` option, so re-running would be a model experiment with no new information. |
| 13 | Python lint / type check (ruff, flake8, mypy, bandit) | — | **Not run.** None is installed or configured, and installing tools was out of scope. |
| 14 | `pip-audit` / `npm audit` | — | **Not run.** They need network access to advisory databases. SEC-22 is from model knowledge only. |
| 15 | `docker compose build` / `up` | — | **Not run.** ARCH-1 was established by an import test that simulated the image contents. |
| 16 | Frontend tests on `main` | — | **Not run.** The scratch worktree has no `node_modules`, and `npm ci` needs network access. |

Reviewer probes (in-process TestClient, scoring of committed samples, reads of score dumps) are listed in each companion document. The audit lead re-ran the ML-2/ML-4 probe and got identical numbers.

## 3. Findings overview

| Source | Critical | High | Medium | Low | Improvement | Total |
|---|---|---|---|---|---|---|
| Security (SEC) | 0 | 5 | 7 | 16 | 1 | 29 |
| Architecture (ARCH) | 0 | 4 | 12 | 10 | 4 | 30 |
| Production ML (ML) | 0 | 4 | 6 | 11 | 2 | 23 |
| Research methodology (RES) | 0 | 4 | 11 | 6 | 1 | 22 |
| **Total** | **0** | **17** | **36** | **43** | **8** | **104** |

**Duplicates.** About 7 findings are the same defect seen by two reviewers:

| Finding | Duplicate of |
|---|---|
| ARCH-3 | SEC-5 |
| ARCH-7 | SEC-9 |
| ARCH-8 | SEC-25 |
| ARCH-19 | ML-5 |
| ARCH-4 | ML-13 |
| ARCH-20 (temp dirs) | SEC-21 |
| ARCH-24 | part of SEC-23 |

That leaves **about 97 distinct issues**. REMEDIATION_PLAN.md merges the duplicates.

**Why no Critical findings.** No finding reaches a real network: there is no live enforcement path, as verified in SECURITY_AUDIT §4. No finding invalidates the core LOAFO research result, which is leakage-free and reproduces exactly.

### 3.1 High-severity findings

| ID | Kind | Finding |
|---|---|---|
| SEC-1 | Confirmed (EXEC) | If auth is enabled without a secret, tokens are signed with a public constant, so admin tokens can be forged. |
| SEC-2 | Confirmed (EXEC) | Seed users with published `ChangeMe*` passwords, including admin, are active whenever auth is on. |
| SEC-3 | Confirmed (EXEC/READ) | Unauthenticated by default, and compose publishes port 8000 on all interfaces. Anyone can approve and execute responses. |
| SEC-4 | Confirmed (EXEC) | The body-size limit only checks `Content-Length`, so chunked bodies bypass it (memory DoS). |
| SEC-5 / ARCH-3 | Confirmed (EXEC) | Alembic `fileConfig` at startup disables the app's security, error and audit loggers. The ingest audit is lost entirely. |
| ARCH-1 | Confirmed (EXEC, simulated image) | The Docker API image cannot start (`cyberrange/`, `research/` and the replay pool are not copied). |
| ARCH-2 | Confirmed (EXEC) | Risk is read with the wrong key, so gate-only incidents and every Live Monitor flow show risk 0. |
| ARCH-4 | Confirmed (EXEC) | The default "Quick score" CSV mode rejects raw CICIDS2017 CSVs. |
| ML-1 | Confirmed (EXEC/READ) | Binary test metrics labelled "@ 0.85" were computed at 0.5. |
| ML-2 | Confirmed (EXEC) | At the deployed 0.85 threshold, WebAttack detection is 41.6 % and Bot 58.5 %. The headline macro-F1 hides this. |
| ML-3 | Confirmed (READ) | The P10 temporal holdout (Friday F1 0.9977) scores the model's own training rows. |
| ML-4 | Confirmed (EXEC) | The "advisory" gate raises incidents under the default `union` policy, which multiplies the benign incident rate about 9× (0.09 % → 0.81 %). |
| RES-1 | Confirmed | README states an unconditional FPR guarantee and that recalibration "restores" control. Per-day realised FPR still reaches about 10 %. |
| RES-2 | Confirmed (EXEC) | Conformal ties make tree-model arms over-conservative (DT 0.31 % FPR at α = 1 %). This breaks R3 hypotheses H1 and H4. |
| RES-3 | Confirmed (EXEC) | The paper omits the per-day fusion inversion (XGB 0.325 vs Aegis 0.088 known recall) and generalises from 2 selected days. |
| RES-4 | Confirmed (EXEC) | "Inversion specific to cross-network" is contradicted by the temporal records at matched FPR. |

### 3.2 What is verified sound

**Research**
* No train/test leakage in either the frozen pipeline or Aegis-OSR.
* No test-based selection of models or thresholds.
* Feature order is identical between training and inference.
* Conformal calibration is implemented correctly.
* Statistics are computed at seed level.
* Every paper number traces to an artifact.
* Exact reproduction holds: regression gate PASS.

**Data**
* Served demo and replay data contain no training rows.
* Alembic migrations show zero drift from the ORM.

**Security**
* No SQL injection, SSRF, path traversal, command injection or reachable unsafe deserialization.
* No committed secrets.
* No route reaches a real network.

**Code structure**
* No top-level import cycles.
* Every frontend API call maps to an existing route.

## 4. Remaining uncertainties

| # | Uncertainty |
|---|---|
| 1 | Docker behaviour, real uvicorn behaviour with chunked bodies, nginx behaviour, and multi-worker behaviour were reasoned about or simulated, not run (SECURITY_AUDIT §6, U-1 … U-8). |
| 2 | The header format of the Python cicflowmeter package is not verified (ML-9). The tool is not installed. |
| 3 | The dependency CVEs are from model knowledge (SEC-22). |
| 4 | Whether the 2018 CSV rows are in time order (RES-14). |
| 5 | Whether Destination Port acts as a shortcut feature (ML-10, RES-12). It is used, but its effect has not been measured. |
| 6 | Four closest related papers remain unread (RESEARCH_ALIGNMENT_REVIEW §2). |
| 7 | Some reviewer line numbers were wrong in LF-terminated script files. The line numbers in these documents were re-verified with `grep -n` for every Critical/High/Medium finding; Low items rely on the reviewer's citation where no line was re-checked. |

## 5. Verdict

**Are we architecturally, technically, scientifically and methodologically aligned with the intended Aegis research goal?**

**Not yet, though the direction is right.** Per dimension (details in RESEARCH_ALIGNMENT_REVIEW.md):

| Dimension | Verdict | Main reasons |
|---|---|---|
| Architectural | Partially | Coherent pipeline and safe defence boundary. Not modular at the serving layer. Deployment is broken (ARCH-1, ARCH-13). Single-process state. |
| Technical | **No** | Tests pass but miss user-visible defects (ARCH-2/3/4) and an absent authentication posture (SEC-1/2/3). |
| Scientific | Partially | The core result is sound and reproducible. Several public claims exceed the evidence (ML-1/2/3, RES-1/3/4). |
| Methodological | Partially | Strong reproducibility practice, but R3 is not ready to run (RES-2, RES-10), and design flows overlap evaluation flows (RES-6). |

ARCH-18 was raised from Low to Medium by the audit lead: a viewer `GET` can overwrite a **frozen v1.1 file** (`global_shap_summary.json`).

The next milestone is correctness and honesty, not new features or compute. See `docs/roadmap/REMEDIATION_PLAN.md`.
