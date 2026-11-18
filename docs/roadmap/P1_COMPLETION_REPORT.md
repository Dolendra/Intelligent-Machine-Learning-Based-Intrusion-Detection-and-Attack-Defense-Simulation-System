# Phase 1 — P1 completion report (application and ML reliability)

**Date:** 2026-11-18
**Branch:** `remediation/phase1-application-ml`, local and not pushed. It is based on `remediation/phase1-correctness` @ `7ffd5f1`, which descends from `d0194a4`.
**HEAD:** `12ea30d`.

**What was not touched:**
* `main` (`775e9a9`) and `v3-openset-research` (`440dec4`) are unchanged, both locally and on `origin`.
* The 16 frozen v1.1 files are identical to tag `v1.1-research`.
* `verify_manifest() == {}`. There are no changes under `research_artifacts/`, `results/` or `models/`, and none to the paper sources.
* No model was retrained, no dataset was touched, and no experiment was run.

**Diff:** 13 commits; 31 files changed, +1,113 / −111.

## 1. Findings resolved

### Batch A — data and ML correctness

| # | Commit | Finding | Change |
|---|---|---|---|
| A1 | `9a83066` | ARCH-1, R-06 compose | The API image now copies `cyberrange/`, `research/` and the replay pool. `.dockerignore` excludes `.env*`, the venvs, the 2018 data and the 1.3 GB of score dumps. Compose binds to loopback, runs `AEGIS_ENV=production` with auth on, and requires `AEGIS_AUTH_SECRET`. |
| A2 | `1bc70aa` | ARCH-4 / ML-13 | `/predict/batch/csv` (the UI default) uses the single ingestion parser, so raw MachineLearningCVE files are accepted. |
| A3 | `f9f604e` | ML-9 | The snake_case headers of Python `cicflowmeter` map onto all 78 features. PCAP extraction is marked `experimental`. |
| A4 | `9d6d6cc` | ML-8 | JSON NaN/Infinity returns 422 instead of 500. In files, bad rows are rejected individually with their line numbers and the other rows are still scored. |
| A5 | `632a3eb` | ML audit A.1 (parity) | Regression tests pin training/inference parity: same 78-feature order everywhere, the training-fitted transform, and results independent of key order. |
| A6 | `50c9699` | ML-14 | Zero-filling missing features only happens with DEMO_MODE in development/test. `missing_features` and `prediction_quality` are always reported. A degraded verdict never raises an incident. |
| A7 | (model failure) `8d74b2e` | model loading | Corrupt or incompatible artifacts return 503 and fail readiness instead of a 500. The model reloads once the artifacts are restored. |

**Batch A gate (passed before Batch B started):**
* 428 tests passed.
* 182 security and remediation tests passed with rate limiting on.
* Frontend: 49 tests pass, type-check passes.
* No changes to any frozen or historical artifact.

### Batch B — application reliability

| # | Commit | Finding | Change |
|---|---|---|---|
| B8 | `81ac88e` | ARCH-5, ARCH-6 | The final VERIFIED status is persisted, and the P6 test is tightened to check it. "Simulate" no longer reopens Resolved or FalsePositive incidents. |
| B9 | `4fc78bd` | ARCH-12 | Incident and campaign IDs carry 48 random bits (was 24) and are retried on collision. |
| B10 | `f7cd428` | ARCH-9 | Queue job retention is bounded, input flows are released after use, and per-flow results can be retrieved (`?include_results=true`). |
| B11 | `54d139a` | ARCH-7 / SEC-9 | Upload parsing, scoring and the cicflowmeter subprocess run in the threadpool, and the WebSocket DB polling runs off the event loop. |
| B12 | `ea7166a` | SEC-10, SEC-11 | Client IP is taken from `X-Forwarded-For` only when the request comes from `AEGIS_TRUSTED_PROXIES`, and nginx now sends that header. The rate limiter now wraps auth, so failed authentication attempts count against the limit. |
| B13 | `12ea30d` | ARCH-15 | CI now runs on the v3, audit and remediation branches. It sets `AEGIS_ENV=test`, checks frozen and protected artifact integrity, runs Alembic upgrade and check, runs an advisory ruff check, smoke-tests the container start, and uses Node 22. |

## 2. Tests (all actually run)

**Evidence that the new tests catch the defects:** each new test was run against the stashed old code and failed there. Exceptions:
* A5 is verification only.
* B13 is configuration.
* B12's tests cannot import on the old code, because the helper they test did not exist.

**Final results**

| Command | Result |
|---|---|
| `MPLBACKEND=Agg DISABLE_RATE_LIMIT=true python -m pytest tests -q -p no:cacheprovider` | **449 passed**, 0 failed, 0 skipped (397 at the end of P0) |
| Security, R1a and all `test_remediation_*` suites with **rate limiting on** | **210 passed** |
| `npm run typecheck` / `npm test` / `vite build` | pass / 49 passed / pass |
| `alembic upgrade head` + `alembic check` on a fresh DB | no drift |
| `verify_manifest()` / `frozen_v11_diff()` | `{}` / `[]` |
| `database/ids.db` modification time | unchanged (01:50:43) |

**New test files (49 tests)**

| File | Tests |
|---|---|
| `test_remediation_r09_docker` | 4 |
| `test_remediation_r10_csv` | 5 |
| `test_remediation_r12_cicflowmeter` | 4 |
| `test_remediation_r11_nonfinite` | 7 |
| `test_remediation_parity` | 4 |
| `test_remediation_r11_missing` | 4 |
| `test_remediation_model_failure` | 3 |
| `test_remediation_r14_r15_lifecycle` | 4 |
| `test_remediation_r16_ids` | 2 |
| `test_remediation_r22_queue` | 3 |
| `test_remediation_r13_nonblocking` | 2 |
| `test_remediation_r17_ratelimit` | 5 |
| `test_remediation_r19_ci` | 5 |

One existing test was tightened: the P6 restart test no longer accepts `SUCCEEDED`.

## 3. Behaviour changes

* `docker compose up` now needs `AEGIS_AUTH_SECRET` (at least 32 characters) and the `AEGIS_SEED_PASSWORD_<USER>` values in the project `.env`. Both ports are bound to 127.0.0.1.
* Uploads with some bad rows are partially scored. The rejected rows are listed in `ingest_validation` and `validation.rejected_rows`.
* Predictions report `missing_features`, `prediction_quality` and `zero_day_status`.
* Incident and campaign IDs are longer: `INC-` + 12 hex characters.
* `GET /api/ingest/queue/{id}?include_results=true` returns per-flow results.

## 4. Remaining defects and risks

1. **Docker was not verified for real.** The Docker Desktop daemon was not running, so there was no `docker build` or `up`. ARCH-1 is fixed and tested by simulating the image's contents, but these remain unverified until a real build runs:
   * the CI container smoke step;
   * the `chmod` on the database bind mount;
   * the nginx `X-Forwarded-For` path (U-1).
   * **To verify:** start Docker Desktop, set `AEGIS_AUTH_SECRET` in `.env`, run `docker compose up --build`, and check `curl http://127.0.0.1:8000/api/ready`.
2. **CI has not run.** Nothing was pushed, so the new workflow is checked only by the local tests that pin its configuration.
3. **The PCAP path is experimental.** The header mapping is fixed, but the tool is not installed, its exact headers are unverified, and unit parity with the 2017 extractor is unvalidated.
4. **Queue detections still do not create incidents.** This is a product decision.
5. **Still open from the remediation plan (P2/P3, not started):**
   * nginx WebSocket upgrade and same-origin `wsUrl` (ARCH-13);
   * CORS ordering (ARCH-14);
   * nginx `client_max_body_size` (ARCH-24);
   * LIME background and class (ML-6/7);
   * token revocation and API-key handling (SEC-12/13/14);
   * scheduled sweep of expired actions and retention (ARCH-11);
   * multi-worker enforcement (ARCH-8);
   * hashed dependency lock (SEC-22, R-18; deferred because changing the lock needs network access and a regression-gate re-run);
   * P3 maintainability items.
6. **Phase 2 claim corrections are still pending:** ML-1/2/3/4/12, RES-1/3/4/11, `docs/IMPLEMENTATION_STATUS.md`, and decision E.
7. **Local user tasks are still open:**
   * `AEGIS_ENV=development` is not in `.env`.
   * Credential rotation in `database/ids.db` (`scripts/70_rotate_credentials.py --legacy`) has not been confirmed.

## 5. Next

Stop for approval. Recommended next step: run the real Docker verification above (it needs Docker Desktop running), then the Phase 2 research-claim corrections.
