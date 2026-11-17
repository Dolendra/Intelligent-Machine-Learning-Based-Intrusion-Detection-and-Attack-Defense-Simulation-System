# Phase 1, P0 remediation report

**Date:** 2026-11-18
**Branch:** `remediation/phase1-correctness` (local; not pushed; nothing merged)
**Base:** `audit/full-repository-2026-11` @ `dc76564`
**Head:** `5aee751`

**Untouched:**
* `main` = `775e9a9` and `v3-openset-research` = `440dec4`, locally and on `origin`.
* The 16 frozen v1.1 files: identical to tag `v1.1-research`.
* The 25 manifest-protected artifacts: `verify_manifest() == {}`.
* No model was retrained, no dataset was touched, and no experiment was run.

## 1. Commits (one per task)

| # | Commit | Task | Findings resolved |
|---|---|---|---|
| 1 | `8da9a80` | Authentication fails closed outside development | SEC-3 (default posture), SEC-28, part of ARCH-27 |
| 2 | `a3f6a4b` | Forgeable token secret and published seed passwords removed; rotation tool added | SEC-1, SEC-2, SEC-7 (API key as signing key); new test-isolation defect fixed |
| 3 | `e3a6c0a` | Response approval authorization: four-eyes rule; gate-only evidence is advisory; admin-only user list | SEC-24, part of SEC-3, part of R-27 |
| — | `fbb4660` | Operational incident policy defaults to `frozen`; gate alerts listed for analyst review | ML-4 (user decision 2) |
| 4 | `a9f889e` | Body-size limits enforced on the streamed bytes, including chunked uploads | SEC-4, CSV-size part of SEC-20 |
| 5 | `71748a3` | Frozen and protected artifacts cannot be overwritten (runtime, savers, scripts) | ARCH-18, RES-17 (PR-09) |
| 6 | `7af6516` | Security, error and upload-audit logging restored; failed logins recorded | SEC-5 / ARCH-3, ARCH-22, SEC-8 |
| 7 | `c6c6029` | Zero-Day Gate failures are visible, isolated per row, and no longer cached forever | ARCH-10, ML-22 |
| 8 | `39aeb5f` | Risk read via the correct key; gate-only risk uses measured intensity | ARCH-2, ML-5, ARCH-19 |
| 9 | `5aee751` | Response audit trail is append-only; incident edits name the real actor | SEC-6, SEC-18 |

**Overall diff:** 61 files changed, +1,689 / −172.
* About half of the additions are the 9 new regression-test files.
* Application changes are limited to: backend middleware and routes, `security/auth`, `security/response`, `security/risk`, `research/serving.py`, `ml` savers, `alembic/env.py`, `database/db.py`, `config.yaml` (incident policy only), the launchers and 13 guarded scripts.

## 2. Tests

**Regression-test files added**

| Test file | Tests |
|---|---|
| `test_remediation_r05_posture.py` | 16 |
| `test_remediation_r05_credentials.py` | 12 |
| `test_remediation_r27_approval.py` | 9 |
| `test_remediation_policy_frozen_default.py` | 4 |
| `test_remediation_r07_body_limits.py` | 7 |
| `test_remediation_r03_frozen_writes.py` | 31 |
| `test_remediation_r02_logging.py` | 5 |
| `test_remediation_r04_gate_failures.py` | 8 |
| `test_remediation_r01_risk.py` | 5 |
| `test_remediation_r08_audit.py` | 3 |
| **Total** | **100** |

**Fail-before / pass-after evidence**

The old code was stashed and the new tests run against it; the code was then restored.

| Fix | Result against the old code |
|---|---|
| R-07 | Did not finish within 10 minutes, because a 40 MB chunked CSV reached pandas. The run was stopped. |
| R-02 | 2 failed |
| R-01 | 3 failed |
| R-08 | 1 failed |
| R-05 | The forged-token and published-password tests pass only with the new code. |

**Validation run at the end of P0** (all actually executed)

| Command | Result |
|---|---|
| `MPLBACKEND=Agg DISABLE_RATE_LIMIT=true python -m pytest tests -q` | **397 passed** (297 before P0), 0 failed, 0 skipped |
| Security and remediation suites **with rate limiting on** (p4, p5, phase_c, phase_d, p6, final_security_validation, all `test_remediation_*`) | **151 passed** |
| `npm run typecheck` / `npm test` / `vite build` (scratch output dir) | pass / 49 passed / pass |
| `alembic upgrade head` + `alembic check` on a throwaway DB | "No new upgrade operations detected" |
| `verify_manifest()` / `frozen_v11_diff()` | `{}` / `[]` |
| `git diff --quiet v1.1-research HEAD -- <16 frozen files>` | identical |

**Tests changed (not weakened)**

| File | Change |
|---|---|
| `tests/conftest.py` | `AEGIS_ENV=test`; a fresh DB for every session; `IDS_DB_URL` pinned |
| `test_productionization_p4/p5/p6` | Use test-only seed passwords from `tests/_seed_passwords.py` |
| `test_productionization_p11_empirical.py` | The test approved its own proposal; it now uses a second actor. `empirical/experiment.py` already did this. |
| `test_r1a_gate_integration.py` | The union test now selects `union` explicitly |

## 3. Behaviour changes users will notice

1. **The API refuses to start unless `AEGIS_ENV=development` or `test`, or authentication is enabled with a secret of at least 32 characters.** Unset `AEGIS_ENV` means production.
   * `scripts/run_api.bat` and `scripts/start_all.ps1` set `development`.
   * The README and `.env.example` are updated.
   * **The developer `.env` does not set `AEGIS_ENV`**, so a plain `uvicorn backend.main:app` now refuses to start until `AEGIS_ENV=development` is added there or in the shell.
2. Seed accounts no longer have known passwords. Set them with `AEGIS_SEED_PASSWORD_<USER>` or `python scripts/70_rotate_credentials.py`.
3. With auth on, the proposer of a response action cannot approve or execute it (403).
4. Zero-Day Candidate evidence can only lead to ESCALATE or MONITOR, never containment.
5. Under the default `frozen` policy, gate-only alerts raise no incident. They are recorded and listed at `GET /api/zero-day/alerts`.
6. Request logs, 500-error logs, security events and the ingest audit appear in the logs again.

## 4. Credential rotation

* No deployed instance or external credential is known, so nothing external needed rotating.
* `python scripts/70_rotate_credentials.py --check` against the developer database `database/ids.db` reports **admin, analyst, responder, viewer** still on the published passwords.
* They were **not** rotated automatically, because doing so from this session would expose the new passwords in the transcript.
* To rotate: run `python scripts/70_rotate_credentials.py --legacy` in your own terminal. With auth enabled, the API refuses to start until this is done.

## 5. New finding during P0

**The test suite used the developer database.** `IDS_DB_URL` from `.env` takes precedence over the test `IDS_DB_PATH`, so every previous test run read and wrote `database/ids.db` (last modified 01:50, during the audit).
* **Fixed** in commit 2.
* `database/ids.db` is git-ignored and is not a research artifact.
* Since the fix, the suite has not modified it.

## 6. Remaining P0 risks and unresolved items

* **Not validated in a real deployment.** Docker was not built, and nothing ran under real uvicorn with chunked requests or behind nginx. These remain unverified assumptions U-1 to U-3 and U-8. **Production security is not claimed.**
* **Compose cannot start the API.**
  * The image also misses `cyberrange/` and `research/` (ARCH-1, P1 R-09).
  * Compose sets no `AEGIS_ENV` and no auth secrets, so the API now refuses to start. This is fail-closed by design.
  * Loopback binding and nginx-only exposure (R-06 compose part) are P1.
* **The ingest audit is log-only.** It is visible again, but not yet persisted to the database.
* **Remaining token items (P2, R-28):**
  * no revocation on logout;
  * `iat` ignored;
  * API key compared in non-constant time and accepted in the query string;
  * a non-ASCII signature returns 500.
* **The rate limiter is keyed on the socket peer** (SEC-10, P1 R-17).
* **The Cyber Range simulation still defaults its own detector selector to `union`** in the UI. It is a simulation only and was not changed.
* **`docs/IMPLEMENTATION_STATUS.md` and the other claim corrections** (D-track) are Phase 2.

## 7. Next

Stop for review. P1 (R-09 to R-19) starts only after approval.
