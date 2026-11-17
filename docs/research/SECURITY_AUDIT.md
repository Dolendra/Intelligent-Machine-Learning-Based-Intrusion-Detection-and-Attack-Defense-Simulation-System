# Security audit

**Date:** 2026-11-18 (Phase 0, read-only).
**Audited code:** `v3-openset-research` @ `440dec4`. The application layer is the same as on `main` @ `775e9a9`, apart from the v3 routes and the RBAC prefixes added for them.

**Method:**
* An independent reviewer read every route and middleware path.
* The reviewer ran in-process probes with FastAPI TestClient against the real `backend.main:app`, started from the repository root so that startup matches production.
* All probe state was redirected to a scratch directory (`IDS_DB_URL`, `AEGIS_RANGE_RUNS_DIR`, `TMP`, `PYTHONDONTWRITEBYTECODE=1`).
* No network access was made and no Docker image was built or run. The repository was not modified.
* The audit lead re-checked SEC-1 to SEC-4 and SEC-6 against the source with `grep`/`sed`.

**What this audit is not:**
* A clean secret scan (done: all four branch tips and the history of filenames) does **not** establish that the application is secure.
* Passing security tests (48/48, run with rate limiting on) does **not** either. The current tests always set a token secret and only send bodies that carry a `Content-Length` header, so they cannot catch SEC-1 or SEC-4.

**Labels used below:**
* *Confirmed defect:* the issue exists today; it was reproduced or follows deterministically from the code.
* *Potential risk:* the issue depends on deployment conditions that were not exercised.
* *Recommendation:* hardening advice, not a defect.
* *Unverified assumption:* the reasoning relies on a fact that was not checked (listed in §6).
* *Confidence:* EXEC = confirmed by execution; READ = confirmed by reading the code; SUSP = suspected.

---

## 1. Scope and coverage

| # | Item | Status | Findings |
|---|---|---|---|
| 1 | Authentication, authorization, RBAC on every endpoint | Covered | SEC-1, SEC-2, SEC-3, SEC-24; route table §2 |
| 2 | API key handling and rotation | Covered | SEC-7, SEC-12 |
| 3 | Token validation and expiry, revocation, role header, seed users | Covered | SEC-1, SEC-2, SEC-7, SEC-13, SEC-14 |
| 4 | CORS and trusted proxy | Covered | SEC-10; ARCH-14 (CORS on error responses) |
| 5 | Rate limiting, including multi-worker deployments | Covered (multi-worker by reading only) | SEC-10, SEC-11, SEC-20, SEC-25, SEC-28 |
| 6 | Request-size limits, including chunked or streamed bodies | Covered | SEC-4, SEC-20, SEC-23 |
| 7 | File upload, PCAP, cicflowmeter subprocess | **Partial**: cicflowmeter is not installed | SEC-9, SEC-15, SEC-21; ML-9 |
| 8 | SQL injection and ORM usage | Covered | none (§4) |
| 9 | SSRF | Covered | none (§4) |
| 10 | Path traversal | Covered | none (§4) |
| 11 | Command injection | Covered | none; SEC-26 is a forward-looking note |
| 12 | Secrets, logging, sensitive-data exposure | Covered | SEC-5, SEC-8, SEC-15, SEC-16, SEC-28 |
| 13 | Unsafe deserialization | Covered | none reachable from input; SEC-23 (writable model directory) |
| 14 | Dependency vulnerabilities | **Partial**: offline, from model knowledge only | SEC-22 |
| 15 | Container and deployment | **Partial**: reading only, no image run | SEC-3, SEC-23; ARCH-1, ARCH-13, ARCH-24 |
| 16 | Approval gate and controlled-defence enforcement | Covered | SEC-24, SEC-26 (§4) |
| 17 | WebSocket authorization | Covered | SEC-27; ARCH-17 |
| 18 | Audit-log integrity | Covered | SEC-5, SEC-6, SEC-18 |

## 2. Route and authorization table

**Authentication is OFF by default** (`config.yaml:154` `auth.enabled: false`; `AEGIS_AUTH_ENABLED` is not set in `.env.example` or `docker-compose.yml`). With auth off, every route below is anonymous, including approve/execute, the user list and uploads (EXEC, SEC-3).

When auth is on, `ApiKeyMiddleware.permission_for_request` (`backend/middleware/api_auth.py`) maps method + path prefix to a permission:
* Unknown mutating routes fall through to `admin`, i.e. they fail closed.
* HEAD is treated as a mutation.
* A trailing slash triggers a 307 redirect, after which the path is re-checked.
* OPTIONS bypasses auth, but no route accepts OPTIONS (405).
* WebSockets are exempt from the middleware and are checked inside their handlers.

Role matrix (`security/rbac.py`):

| Role | Permissions |
|---|---|
| admin | all |
| responder | all except `admin` |
| analyst | all except `approve_response` and `admin` |
| viewer | `read_*` only |
| ml_research | `read_*` + `write_detect` |

The route table was generated from the live router (82 HTTP + 2 WebSocket routes):

| # | Method | Path | Required permission | Roles allowed (when auth on) | Where enforced |
|---|---|---|---|---|---|
| 1 | GET | `/api/security/status` | PUBLIC | anyone | `PUBLIC_PATHS` (api_auth.py:15-27) - never authenticated |
| 2 | GET | `/api/metrics` | PUBLIC | anyone | `PUBLIC_PATHS` (api_auth.py:15-27) - never authenticated |
| 3 | GET | `/api/ops/status` | PUBLIC | anyone | `PUBLIC_PATHS` (api_auth.py:15-27) - never authenticated |
| 4 | GET | `/api/health` | PUBLIC | anyone | `PUBLIC_PATHS` (api_auth.py:15-27) - never authenticated |
| 5 | GET | `/api/ready` | PUBLIC | anyone | `PUBLIC_PATHS` (api_auth.py:15-27) - never authenticated |
| 6 | GET | `/api/auth/status` | PUBLIC | anyone | `PUBLIC_PATHS` (api_auth.py:15-27) - never authenticated |
| 7 | POST | `/api/auth/login` | PUBLIC | anyone | `PUBLIC_PATHS` (api_auth.py:15-27) - never authenticated |
| 8 | GET | `/api/auth/me` | any-authenticated | any authenticated | ApiKeyMiddleware (api_auth.py:34-35) |
| 9 | POST | `/api/auth/logout` | any-authenticated | any authenticated | ApiKeyMiddleware (api_auth.py:34-35) |
| 10 | GET | `/api/auth/users` | admin | admin | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 11 | GET | `/api/models` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 12 | GET | `/api/models/health` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 13 | GET | `/api/models/comparison` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 14 | GET | `/api/models/shap/global` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 15 | GET | `/api/experiments` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 16 | GET | `/api/drift` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 17 | POST | `/api/predict` | write_detect | admin,responder,analyst,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 18 | POST | `/api/predict/batch` | write_detect | admin,responder,analyst,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 19 | POST | `/api/predict/batch/csv` | write_detect | admin,responder,analyst,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 20 | GET | `/api/ingest/capabilities` | read_health | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 21 | POST | `/api/ingest/flows/csv` | write_ingest | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 22 | POST | `/api/ingest/pcap` | write_ingest | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 23 | GET | `/api/ingest/queue` | read_health | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 24 | POST | `/api/ingest/queue/submit` | write_ingest | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 25 | POST | `/api/ingest/queue/submit-pcap` | write_ingest | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 26 | GET | `/api/ingest/queue/{job_id}` | read_health | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 27 | POST | `/api/explain` | write_detect | admin,responder,analyst,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 28 | POST | `/api/explain/counterfactual` | write_detect | admin,responder,analyst,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 29 | POST | `/api/risk` | write_detect | admin,responder,analyst,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 30 | POST | `/api/recommendation` | write_detect | admin,responder,analyst,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 31 | POST | `/api/response/plan` | write_detect | admin,responder,analyst,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 32 | GET | `/api/response/capabilities` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 33 | GET | `/api/response/actions` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 34 | POST | `/api/response/actions/propose` | write_response | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 35 | GET | `/api/response/actions/{action_id}` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 36 | GET | `/api/response/actions/{action_id}/audit` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 37 | POST | `/api/response/actions/{action_id}/dry-run` | write_response | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 38 | POST | `/api/response/actions/{action_id}/approve` | approve_response | admin,responder | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 39 | POST | `/api/response/actions/{action_id}/reject` | approve_response | admin,responder | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 40 | POST | `/api/response/actions/{action_id}/execute` | approve_response | admin,responder | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 41 | POST | `/api/response/actions/{action_id}/rollback` | approve_response | admin,responder | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 42 | POST | `/api/response/actions/{action_id}/expire` | approve_response | admin,responder | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 43 | POST | `/api/response/actions/sweep-expired` | approve_response | admin,responder | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 44 | GET | `/api/response/adapters` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 45 | POST | `/api/incidents/{incident_id}/response/propose` | write_incidents | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 46 | GET | `/api/incidents/{incident_id}/response/actions` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 47 | POST | `/api/simulation/start` | write_simulation | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 48 | GET | `/api/simulation` | read_health | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 49 | GET | `/api/assets` | read_health | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 50 | GET | `/api/campaigns` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 51 | GET | `/api/campaigns/{campaign_id}` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 52 | POST | `/api/campaigns/{campaign_id}/simulate` | write_incidents | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 53 | POST | `/api/simulation/from-prediction` | write_simulation | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 54 | POST | `/api/simulation/advance` | write_simulation | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 55 | GET | `/api/simulation/{session_id}` | read_health | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 56 | GET | `/api/incidents` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 57 | GET | `/api/incidents/{incident_id}` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 58 | GET | `/api/incidents/{incident_id}/trace` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 59 | PATCH | `/api/incidents/{incident_id}` | write_incidents | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 60 | POST | `/api/incidents/{incident_id}/simulate` | write_incidents | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 61 | GET | `/api/analytics` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 62 | GET | `/api/export/incidents.json` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 63 | GET | `/api/export/incidents.csv` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 64 | GET | `/api/export/analytics.json` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 65 | GET | `/api/export/report.pdf` | read_incidents | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 66 | WS | `/api/ws/events` | read_incidents | admin,responder,analyst,viewer,ml_research | WS handler: api.py:1160-1205 (`read_incidents`) |
| 67 | GET | `/api/features/template` | read_health | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 68 | GET | `/api/demo/flow` | read_health | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 69 | GET | `/api/demo/flows` | read_health | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 70 | GET | `/api/zero-day/status` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 71 | POST | `/api/zero-day/assess` | write_detect | admin,responder,analyst,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 72 | GET | `/api/research/overview` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 73 | GET | `/api/research/openset/{protocol}` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 74 | GET | `/api/live/scenarios` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 75 | WS | `/api/ws/live` | read_models | admin,responder,analyst,viewer,ml_research | WS handler: v3.py:100-128 (`read_models`) |
| 76 | GET | `/api/range/scenarios` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 77 | GET | `/api/range/runs` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 78 | POST | `/api/range/runs` | write_simulation | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 79 | GET | `/api/range/runs/{run_id}` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 80 | POST | `/api/range/runs/{run_id}/step` | write_simulation | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 81 | POST | `/api/range/runs/{run_id}/respond` | write_simulation | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 82 | POST | `/api/range/runs/{run_id}/complete` | write_simulation | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 83 | GET | `/api/range/experiments/latest` | read_models | admin,responder,analyst,viewer,ml_research | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 84 | POST | `/api/range/experiments/sweep` | write_simulation | admin,responder,analyst | ApiKeyMiddleware.permission_for_request (api_auth.py:30-78) |
| 85 | GET | `/`, `/docs`, `/redoc`, `/openapi.json` | PUBLIC | anyone | `PUBLIC_PATHS` |

## 3. Findings

### 3.0 Combined effect

Taken together, SEC-1, SEC-2 and SEC-3 mean that **Aegis has no effective authentication in any documented configuration**:
* In the default configuration, every action is anonymous.
* If auth is enabled as `docs/STAGE2_PRODUCTION.md` describes, an admin token can be forged from a constant that is published in the source, and the admin password is also published.

The impact is limited to the integrity and availability of IDS data, because no code path reaches a real network (§4). This is why these are High rather than Critical. The P4/P5/P12 security claims in the `main` branch documentation (`docs/FINAL_SECURITY_VALIDATION.md`, "overall PASS") do **not** hold for a deployment that follows the shipped defaults.

### 3.1 High

#### SEC-1 — High — Confirmed defect (EXEC) — The token HMAC key falls back to a public constant, so admin tokens can be forged
* **Where:** `security/auth/tokens.py:20-25`. The function `auth_secret()` returns `AEGIS_AUTH_SECRET`, then falls back to `AEGIS_API_KEY`, then to the literal `"aegis-dev-only-change-me"`. It is used both to mint and to verify tokens.
* **Evidence:** with `AEGIS_AUTH_ENABLED=true` and no secret or key set:
  * a token forged with `HMAC-SHA256("aegis-dev-only-change-me", …{"username":"admin"})` gets 200 on `/api/auth/users` and `/api/auth/me` (role admin);
  * no credentials gets 401.
  * Nothing warns or fails at startup.
  * `.env.example:21` leaves `AEGIS_AUTH_SECRET` commented out.
* **Exploitability:** remote and unauthenticated, under the documented way of turning auth on (enable the flag, no secret).
* **Impact:** full admin access (approve/execute, the user list).
* **Remediation:**
  * Refuse to start when auth is enabled unless `AEGIS_AUTH_SECRET` is set, at least 32 random bytes, and different from the API key.
  * Remove both fallbacks.
* **Verification test:**
  * Startup with auth enabled and no secret raises.
  * With a secret set, a token signed with the constant gets 401.

#### SEC-2 — High — Confirmed defect (EXEC) — Seed accounts with passwords published in the source, including admin, are active whenever auth is on
* **Where:**
  * `security/auth/users.py:17-20`: `("admin","admin","ChangeMeAdmin!")`, plus the responder, analyst and viewer accounts.
  * Seeded by `database/bootstrap.py` on every `init_db()` when the users table is empty.
  * The overrides `AEGIS_SEED_PASSWORD_*` are optional and commented out.
* **Evidence:**
  * Logging in with `admin`/`ChangeMeAdmin!` returns 200 and an access token.
  * There is no forced password change and no endpoint to change a password.
* **Exploitability:** remote and unauthenticated, once auth is on.
* **Remediation:**
  * Never seed known passwords when auth is enabled. Generate them once and print them, or require the seed environment variables.
  * Refuse to start if any `ChangeMe*` password still verifies.
* **Verification test:** on a fresh database with auth on, `admin`/`ChangeMeAdmin!` gets 401 (or startup fails).

#### SEC-3 — High — Confirmed defect (EXEC for the app; READ for compose) — The shipped default is unauthenticated, and compose publishes the API on all interfaces
* **Where:**
  * `config.yaml:154` sets auth off.
  * `backend/middleware/api_auth.py` passes requests straight through when auth is not required.
  * `docker-compose.yml:7` (`"8000:8000"`), `:11` (`DEMO_MODE: "true"`) and `:26` (`"5173:80"`).
  * `/api/auth/users` explicitly allows anonymous access.
* **Evidence (default configuration):**
  * Anonymous propose: 200. Anonymous approve: 200, and the action executes.
  * The anonymous user list returns admin.
  * Both WebSockets accept anonymous connections from any origin.
* **Mitigating context:** this is documented as "demo open access", and the UI labels it.
* **Impact:** anyone who can reach port 8000 or 5173 can:
  * propose, approve, roll back and expire response actions;
  * rewrite incidents;
  * upload files;
  * enumerate users;
  * purge the audit trail (SEC-6);
  * exhaust memory (SEC-4).
* **Remediation:**
  * Fail closed outside `AEGIS_ENV=development`.
  * Publish only nginx, bound to loopback or behind TLS.
  * Enable auth in compose, with secrets from `env_file`.
  * Remove the anonymous branch of `/auth/users`.
* **Verification test:**
  * Startup with `AEGIS_ENV=production` and auth off fails.
  * Anonymous `/auth/users` gets 401 or 403.

#### SEC-4 — High — Confirmed defect (EXEC) — Request-size limits are bypassed by chunked bodies, enabling memory denial of service
* **Where:**
  * `backend/middleware/request_limits.py:55-57`: if the `content-length` header is missing, the request is passed straight to the handler.
  * The handlers `await file.read()` or parse the whole JSON body.
* **Evidence:**

  | Request | Result |
  |---|---|
  | 40 MB PCAP with Content-Length | 413 from the middleware |
  | 40 MB PCAP chunked | read in full before the handler returned `PCAP_TOO_LARGE` |
  | 5 MB chunked JSON PATCH (limit 1 MB) | accepted and parsed |
  | 12 MB chunked CSV | 3.1 M rows parsed before the 500-row cap applied |

* **Assumption:** that real uvicorn accepts chunked bodies the same way is unverified (U-2).
* **Exploitability:** remote; anonymous by default. Port 8000 is published directly, so nginx buffering does not help.
* **Impact:** the documented P5 "DoS / memory protection" control does not hold.
* **Remediation:**
  * Count the bytes actually received in a pure ASGI middleware, so the limit applies whether or not Content-Length is present.
  * Read uploads in bounded chunks.
  * Set nginx `client_max_body_size`.
* **Verification test:**
  * A 5 MB chunked JSON body and a 40 MB chunked PCAP both get 413 from the middleware before the handler runs.
  * Process memory (RSS) stays bounded.

#### SEC-5 — High — Confirmed defect (EXEC) — Startup migration disables the security, error and audit loggers
This is the security consequence of ARCH-3.
* **Where:**
  * `alembic/env.py:20` calls `fileConfig(...)`, whose default `disable_existing_loggers=True` disables every logger created before it.
  * `alembic.ini` sets the root level to WARN.
  * It runs on every startup.
* **Evidence:** after startup, `aegis.security`, `aegis.api.errors` and `aegis.ops` are disabled, and root is at WARNING.
* **Consequences:**
  * **The ingest audit (`ingestion/audit.py`) is log-only, so no upload is recorded anywhere.**
  * Unhandled 500 errors are never logged.
  * Security events and login records survive only as database rows (`security_audit_events`), not as log lines.
* **Impact:** the claimed P7 structured logs and P1 ingest audit do not function. This also removes detection and forensics for every other finding in this document.
* **Remediation:**
  * Call `fileConfig(..., disable_existing_loggers=False)`, and only when Alembic is run from the CLI.
  * Persist the ingest audit to the database.
* **Verification test:**
  * After lifespan startup, `logging.getLogger("aegis.security").disabled is False` and root ≤ INFO.
  * A rejected PCAP produces an ingest-audit record.

### 3.2 Medium

| ID | Kind | Where | Evidence / exploitability | Impact | Remediation / verification test |
|---|---|---|---|---|---|
| SEC-6 | Confirmed defect (EXEC) | `security/response/store.py:163-184` (count-based pruning with `.delete()`), documented as append-only at `database/db.py:149` | Proposing 502 actions deleted the entire audit trail of an earlier executed action | An insider can erase who approved and executed an action (repudiation) | Remove the pruning and add a hash chain. **Test:** the audit rows of an executed action survive N new proposals. |
| SEC-7 | Confirmed defect (EXEC) | `security/auth/tokens.py:20-25` (API key reused as the HMAC key); role-header override; `/security/status` | A holder of a non-admin API key can mint a bearer token for any user. `AEGIS_ALLOW_ROLE_HEADER=true` lets a request claim admin. With the default `api_key_role: admin` there is nothing to escalate. | Privilege escalation under non-default configurations | Use a separate secret, and allow the role header only in development. **Test:** a token minted with the API key is rejected. |
| SEC-8 | Confirmed defect (EXEC) | `security/auth/service.py:22-26`; `backend/routes/api.py` `auth_login` | A failed password login produces no `security_event`, no metric, and no log line (the log is suppressed, SEC-5) | An IDS that cannot see brute force against itself | Record login failures and successes; add per-account backoff. **Test:** a failed login writes a security-event row. |
| SEC-9 | Confirmed (READ) | `backend/routes/api.py:379,465` and the other upload handlers (`async def` doing blocking work) | One upload freezes all HTTP traffic, both WebSockets and the health checks (same finding as ARCH-7) | Denial of service; the container is restarted | Use `def` handlers or `run_in_threadpool`, and an async subprocess. **Test:** `/health` latency stays low during a CSV/PCAP job. |
| SEC-10 | Confirmed (READ) | `backend/middleware/rate_limit.py` (keyed on `request.client.host`); nginx proxy; uvicorn `forwarded_allow_ips` default (U-1) | Behind the shipped nginx every user shares one bucket, so 10 bad logins per minute lock everyone out. Limits multiply with N workers. | Lock-out denial of service; ineffective limits | Forward the client IP, configure trusted proxies, use a shared limiter. **Test:** two distinct client IPs get separate buckets through the proxy. |
| SEC-23 | Potential risk (READ) | `docker-compose.yml`, `Dockerfile.api`, `Dockerfile.frontend`, `frontend/nginx.conf` | Port 8000 bypasses nginx; no TLS; the model directory is writable by the runtime user; nginx body limit 1 MB (ARCH-24); no security headers on the frontend | Widens every other finding; plaintext credentials on the wire | Expose nginx only, add TLS, read-only model mount, non-root user, headers. **Test:** a compose smoke test. |
| SEC-24 | Potential risk (EXEC for behaviour) | `security/response/service.py` `approve_action` → execute; `security/rbac.py` (responder has both `write_response` and `approve_response`) | One account can take an action from proposal to ACTIVE with no second person | Today only the simulated control plane is affected. If a real adapter is ever added, the "human approval gate" is a single person. | Four-eyes approval (approver ≠ proposer) before any real adapter. **Test:** a self-approval gets 403. |

### 3.3 Low and improvement

| ID | Kind | Where | Summary | Remediation |
|---|---|---|---|---|
| SEC-11 | Confirmed (EXEC) | `backend/main.py` (auth runs outside the rate limiter) | Failed API-key/token attempts are never rate-limited, and each failure writes a database row | Put the limiter outside auth, or add an auth-failure limiter |
| SEC-12 | Confirmed (EXEC/READ) | `backend/middleware/api_auth.py:177-178, 254` | Non-constant-time key comparison; key accepted in the query string; single static key; rotation requires a restart | Use `hmac.compare_digest`; accept headers only; support multiple keys |
| SEC-13 | Confirmed (EXEC) | logout route (no-op); `security/auth/tokens.py` | No revocation on logout or password change; `iat` is ignored; no maximum lifetime (8 h) | Add a `token_version`; check `iat` |
| SEC-14 | Confirmed (EXEC) | `security/auth/tokens.py:62` (`compare_digest` on `str`) | A non-ASCII signature causes an unhandled 500, with no auth-failure event | Compare bytes, or catch `TypeError` |
| SEC-15 | Confirmed (EXEC) | public `/security/status`, `/ops/status`, `/ready`, `/docs`; error details | Exposes absolute paths, the database location, user count, limiter/auth configuration and the OpenAPI surface | Trim public payloads; disable docs in production |
| SEC-16 | Confirmed (EXEC) | `backend/routes/api.py:57-108` | `/security/status` reports configuration values, not the effective ones, and ignores the `DISABLE_*` switches | One shared helper for effective settings (see ARCH-27) |
| SEC-17 | Confirmed (EXEC) | `security/auth/users.py:168-174` | Login timing reveals whether a username exists (PBKDF2 is skipped for unknown users) | Verify against a dummy hash |
| SEC-18 | Confirmed (EXEC) | incident update path | Incident status changes are attributed to a hard-coded `"analyst"` | Pass the real actor |
| SEC-19 | Confirmed (EXEC) | `backend/services/pipeline.py:996-1018`; `IncidentUpdateRequest` (no length limits) | CSV export formula injection through `defense_action` | Neutralise cells starting with `= + - @`; add `max_length` |
| SEC-20 | Confirmed (EXEC/READ) | range endpoints, CSV parse before the row cap, `limit` parameters, WebSockets | Unbounded work | Rate-limit and cap these paths |
| SEC-21 | Confirmed (READ) | `ingestion/cicflowmeter_runner.py:33` (`mkdtemp`, never removed) | PCAP-derived flow CSVs (with IPs) persist in temp, despite `temp_files_hours: 1` in the retention config | Use `TemporaryDirectory()` |
| SEC-22 | Potential risk (READ; CVEs SUSP) | `requirements-lock.txt` (`python-multipart==0.0.6`, among others); `Dockerfile.api` installs `requirements.txt` (version floors only) | The lock file pins a version believed to be vulnerable, and Docker ignores the lock anyway | Regenerate a hashed lock; install from it; add `pip-audit`/`npm audit` to CI |
| SEC-25 | Potential risk (READ) | in-process state; startup recovery | Not process-safe with multiple workers (same as ARCH-8) | Enforce a single process, or use shared state |
| SEC-26 | Recommendation (EXEC) | `security/response/service.py:37-43` | The response target is validated with a deny-list. This is safe only because no shell is involved; `$(id)` is rejected with 422 today. | Validate against an allowlist (`ipaddress` / RFC 1123) |
| SEC-27 | Potential risk (READ) | `frontend/src/services/api.ts:9-27, 1362` | The token is stored in localStorage and sent in the WebSocket query string | Use the WebSocket subprotocol or a short-lived ticket |
| SEC-28 | Confirmed (EXEC) | `DISABLE_API_AUTH`, `DISABLE_RATE_LIMIT`, `DISABLE_REQUEST_LIMITS`, `AEGIS_EXPOSE_ERRORS` | No production guard on these kill switches | Honour them only in development/test, and warn at startup |
| SEC-29 | Potential risk (READ) | `scripts/40_db_backup_restore.py:42-48, 75-80, 191-196` | Backups are plaintext; restore deletes the target before verifying the backup; the default path ignores `IDS_DB_URL` | Verify before replacing; respect the configured URL |

## 4. Verified not vulnerable

* **SQL injection:** none found.
  * All queries go through the ORM with bound parameters.
  * The only raw SQL uses constant strings (`PRAGMA`, fixed `ALTER TABLE`, `SELECT 1`).
  * The backup script interpolates table names only from a constant list.
* **SSRF:** none.
  * There is no outbound HTTP or socket use in `backend/`, `security/`, `ingestion/`, `database/`, `cyberrange/` or `research/serving.py`.
  * Threat intelligence is a static MITRE map.
* **Path traversal:** none. Protocols and scenarios are checked against allowlists, run IDs are generated by the server, and no user-controlled path reaches the filesystem.
* **Command injection:** none.
  * The only subprocess reachable from the API is the cicflowmeter call, which passes an argument list.
  * There is no `shell=True`, `os.system`, `eval` or `exec` on input.
* **Deserialization:** none reachable from input.
  * `joblib.load` reads only fixed artifact paths.
  * `np.load` keeps `allow_pickle=False`.
  * YAML is read with `yaml.safe_load`.
* **Controlled defence:** no API call can reach a real network or firewall. There are three independent guards:
  * the mode check rejects `LIVE` (EXEC: 422 `LIVE_MODE_DISABLED`);
  * proposal rejects adapters marked `touches_real_network` (EXEC: 422 `LIVE_ADAPTER_FORBIDDEN`);
  * execution re-checks the same condition.

  `LiveNetworkAdapter` raises on every method. Double approval is prevented by an atomic `UPDATE … WHERE status`.
* **Committed secrets:** none, on any of the four branch tips or in the history of filenames (audit lead's scan). `.env` is git-ignored and was never committed.

## 5. Recommendations (priority order)

1. Fail closed at startup on a weak or missing secret, active `ChangeMe*` seeds, auth off outside development, or any `DISABLE_*` switch set in production (SEC-1, SEC-2, SEC-3, SEC-7, SEC-28).
2. Fix logging, and persist the ingest audit and login events to the database (SEC-5, SEC-8).
3. Enforce body size on the actual request stream, and set the nginx limit (SEC-4, SEC-23).
4. Make the response audit truly append-only (hash chain), and attribute every action to its real actor (SEC-6, SEC-18).
5. Compose: expose only nginx, add TLS, configure proxy headers (SEC-10, SEC-23).
6. Move blocking work off the event loop, and bound expensive endpoints (SEC-9, SEC-20).
7. Tokens: add revocation, check `iat`, compare bytes, stop sending tokens in query strings (SEC-13, SEC-14, SEC-27).
8. Require four-eyes approval and allowlist targets before any real adapter exists (SEC-24, SEC-26).
9. Use a hashed lock file in Docker, and add `pip-audit`/`npm audit` to CI (SEC-22).
10. Add a regression test for every verification test above.

## 6. Unverified assumptions

| ID | Assumption | Affects |
|---|---|---|
| U-1 | uvicorn's default `forwarded_allow_ips` is 127.0.0.1 (from model knowledge; not run) | SEC-10 |
| U-2 | Real uvicorn accepts chunked bodies without Content-Length, as TestClient does (high confidence; not run against a live server) | SEC-4 |
| U-3 | nginx's default `client_max_body_size` is 1 MB and nginx buffers request bodies | SEC-4, SEC-23 |
| U-4 | The CVE identifiers and fixed versions cited for SEC-22 come from model knowledge, not an advisory database | SEC-22 |
| U-5 | cicflowmeter is not installed, so its success path and error payloads were read, not run | SEC-9, SEC-15, SEC-21 |
| U-6 | PostgreSQL deployment was not tested | — |
| U-7 | Multi-worker behaviour was not run | SEC-10, SEC-25 |
| U-8 | No Docker image was built or run (and the API image cannot start as shipped, ARCH-1) | SEC-3, SEC-23 |
