# Application architecture audit

**Date:** 2026-11-18 (Phase 0, read-only).

**Audited code:** `v3-openset-research` @ `440dec4`. The application layer is shared with `main` @ `775e9a9` (see FULL_REPOSITORY_AUDIT.md §2 for the branch differences).

**Method:**
- An independent reviewer traced each user action from the frontend through the API, the service layer, the models and the database, and back to the response.
- The reviewer ran probes against scratch SQLite databases (`IDS_DB_URL` overridden, `PYTHONDONTWRITEBYTECODE=1`). `git status` stayed clean.
- The audit lead re-checked every High and Medium finding against the source with `grep -n`; the line numbers below are those verified values.

**Labels:**
- **Confirmed defect:** reproduced, or deterministic from the code.
- **Potential risk:** depends on runtime conditions that were not exercised.
- **Recommendation:** not a defect.
- **EXEC / READ / SUSP:** confidence from execution / from reading the code / suspected.

---

## 1. Component inventory

| Component | Purpose | Inputs → outputs | Error handling | Test coverage |
|---|---|---|---|---|
| `backend/main.py` (147 LOC) | App factory, lifespan, middleware | config/env → FastAPI app | DB init failure aborts startup (clear). Ingest-queue and recovery failures only log warnings. | TestClient-based suites |
| `backend/routes/api.py` (1,254 LOC, 66 handlers) | v1/v2 REST plus `/ws/events` | JSON, multipart, query → JSON/CSV/PDF | Maps FeatureValidationError→422, RuntimeError→503, ResponseError→status, KeyError→404 | test_api, P1–P9 |
| `backend/routes/v3.py` (191) | Zero-Day Gate, research digest, `/ws/live` | flows/WS commands → verdicts/ticks | 503 GATE_NOT_READY; POOL_MISSING message | test_v3_api; useLiveStream.test |
| `backend/routes/range.py` (148) | Cyber range API | run config → range view | 404 / 409 / 422 / 503 | test_cyber_range |
| `backend/services/pipeline.py` (1,200) | Prediction orchestration, incidents, analytics, exports, demo data, CSV parsing, model reports | features → prediction/incident | Gate errors swallowed (`:266`) | test_prediction, test_r1a_gate_integration, golden path |
| `backend/services/live_stream.py` (301) | Live Monitor replay of held-out flows | scenario/rate → ticks | Missing pool raises an error | Frontend only; no backend test of the tick payload |
| `ingestion/*` | CSV/PCAP → schema-aligned flows; in-process queue | bytes → IngestResult/QueueJob | Structured error codes | test_ingestion_* |
| `database/*`, `alembic/` (3 revisions) | ORM, Alembic-first init, seeding, retention | URL → engine/session | Alembic failure → warning + `create_all` fallback | test_decision_trace_alembic, P6 |
| `security/response/*` | Propose → dry-run → approve/execute → verify → rollback/expire | action → audited action | ResponseError codes; atomic `claim_status` | P2, P3, P6, P9 |
| `backend/observability/*`, `backend/recovery/*` | Metrics, health/readiness, ops snapshot; startup recovery | — | Each check reports "unavailable" | test_phase_e, P7, P9 |
| `research/serving.py` | Zero-Day Gate singleton | flows → p-values, labels | Load error cached for the life of the process | test_v3_api |
| `simulation/`, `cyberrange/`, `empirical/` | Illustrative demo; trace-driven simulation; in-process emulation | — | — | test_security_simulation, test_cyber_range, P11 |
| `frontend/src/services/api.ts` (1,375) | Typed client and all API types | — | `ApiError`; a 401 clears the token | api.test.ts (3 tests) |
| `frontend/src/pages/*` (13 routed pages + Login) | UI | — | ErrorState/toasts | Tests exist for 3 pages only (CyberRange, ResearchLab, Simulation) |

**Middleware order,** outermost to innermost (EXEC): Logging → Metrics → SecurityHeaders → ApiKey(Auth) → RateLimit → RequestSize → CORS.

---

## 2. Flow traces (summary)

| Flow | Path | Defects on the path |
|---|---|---|
| Single detection | `DetectionPage.runDetect` → `POST /api/predict` → `api.py:338` → `run_prediction`. Steps: frozen predict → risk/recommendation → gate (errors swallowed) → `detection_policy.decide` (default `union`) → dedup/campaign → Incident + events → ZeroDayAlert → trace | ARCH-2, ARCH-12, ML-4, ML-5 |
| CSV upload | Three UI modes: "Quick score" (default) → `/predict/batch/csv` (`parse_flows_csv`); "validated" → `/ingest/flows/csv`; "queue" → `/ingest/queue/submit` | ARCH-4, ARCH-7, ARCH-9 |
| PCAP upload | `/ingest/pcap` → validation → temp file → `cicflowmeter` **subprocess on the event loop** → normalise | ARCH-7, ARCH-20, ARCH-24, ML-9 |
| Live Monitor | `useLiveStream` → `WS /api/ws/live` → `LiveSession.tick` in `asyncio.to_thread` → frozen + gate scoring | ARCH-2 (risk always 0), ARCH-13, ARCH-17 |
| Incident detail | `GET /incidents/{id}`, `/trace`, `/response/actions`; PATCH status through a state machine; "Simulate" | ARCH-6 |
| Response actions | propose → dry-run → approve (auto-executes) → verify → ACTIVE/VERIFIED → rollback | ARCH-5, ARCH-11, ARCH-23, ARCH-8 |
| Zero-Day lab | `/zero-day/status`, `/zero-day/assess`; types match | ARCH-10 |
| Cyber range | `/range/runs` → step / respond / complete → run JSON written into the repo | ARCH-20, ARCH-8 |
| Reports / exports | `/incidents`, `/analytics`, `/export/{kind}` | CSV export omits `detector_source` / `zero_day_label` |
| Login | `/auth/login` → token in localStorage → `/security/status`, `/auth/me` → Bearer | ARCH-27 (inconsistent auth flag) |

---

## 3. Frontend ↔ backend contract

- **No call to a missing route.** Every path in `api.ts` exists in the backend with the correct method (READ, checked against all three routers).
- **The mismatches are in response semantics:**
  - risk is 0 for gate-only incidents and live flows (ARCH-2);
  - VERIFIED is returned by the API but SUCCEEDED is what is persisted (ARCH-5);
  - the TypeScript `Incident` type lacks `detector_source`, `zero_day_label` and `zero_day_p_value`;
  - `PredictResult` lacks `incident_risk` and `detection_decision`;
  - `/security/status` reports `auth.enabled` while ignoring `DISABLE_API_AUTH`.
- **23 backend routes have no UI caller.** Several are legitimate operator endpoints (`/metrics`, `/ready`, audit). But `/response/actions/{id}/execute`, `/expire` and `/sweep-expired` are lifecycle steps the UI cannot reach.
- **11 client methods are unused.**
- **Only `/predict` and `/health` declare a `response_model`.** The TypeScript types are maintained by hand, which is why the semantic mismatches above went unnoticed.

---

## 4. Findings

### ARCH-1 — High — Confirmed defect — The Docker API image cannot start
- **Where:**
  - `Dockerfile.api:13-20` copies only `ids_config.py`, `config.yaml`, `ml`, `explainability`, `security`, `simulation`, `ingestion`, `backend` and `database`.
  - `backend/routes/range.py:10` (`from cyberrange.engine import …`) is imported at module load by `backend/main.py`.
- **Evidence:** the reviewer imported `backend.main` with the uncopied packages blocked: `IMPORT FAILS: No module named 'cyberrange'` (EXEC, simulated image contents).
  - Not verified: an actual `docker build` + `run` (Docker was not used).
- **Impact:**
  - `docker compose up` builds, but uvicorn crashes on import, and the frontend service never starts because it depends on the API healthcheck.
  - Even after adding `cyberrange/`, the image still lacks `research/` and the replay pool, so every v3 feature would report "unavailable".
- **Remediation:**
  - COPY `cyberrange/`, `research/` (the serving modules) and `research_artifacts/replay/` into the image.
  - Add a CI job that starts the container and polls `/api/ready` and `/api/zero-day/status`.
- **Verification test:** that CI job.

### ARCH-2 — High — Confirmed defect — Risk is read with the wrong key: gate-only incidents and every Live Monitor flow show risk 0
- **Where:**
  - `backend/services/pipeline.py:384`: `g_risk.get("score", 0.0)`, used again at `:397-398`, `:448` and `:480`;
  - `backend/services/live_stream.py:278`: `risk.get("score", 0)`;
  - but `compute_risk` returns the key `risk_score` (`security/risk/engine.py:58`, `:107`).
- **Evidence (EXEC, reviewer; READ, audit lead):** `compute_risk('Zero-Day Candidate', 0.99, True)` has `risk_score` = 55.8, while `.get('score')` returns 0.0.
- **Impact:**
  - Every incident raised only by the Zero-Day Gate is stored with risk 0 and severity MEDIUM. This shows up in incident pages, dashboards, campaign `max_risk`, exports and WebSocket events.
  - Dedup never updates the risk.
  - The Live Monitor shows "0.0 · HIGH" for every flow.
  - This is the v3 headline feature displaying wrong data.
- **Remediation:**
  - Read `risk_score`.
  - Return a typed result from `compute_risk` so that a wrong key fails type checking.
- **Verification test:** a gate-only incident has `risk_score > 0`, and the live tick carries the computed risk.

### ARCH-3 — High — Confirmed defect — The startup migration silences application logging
- **Where:**
  - `alembic/env.py:20` calls `fileConfig(config.config_file_name)`, whose default `disable_existing_loggers=True` disables existing loggers;
  - it runs on every startup via `database/db.py:203-208` (`command.upgrade`) from the lifespan;
  - `alembic.ini` sets the root logger to WARN.
- **Evidence (EXEC, reviewer, full app start):**
  - after startup, `aegis.api`, `aegis.api.errors`, `aegis.security` and `aegis.ops` are disabled, and the root logger is at WARNING;
  - a later `GET /api/health` produced no request log line.
- **Impact:** in every normal run, all of the following are dropped without any sign:
  - the P7 structured request logs;
  - the unhandled-exception log (500s become invisible);
  - security-boundary events;
  - the PCAP upload audit trail (`aegis.ingest.audit`), which exists only in the logs.
- **Remediation:**
  - Call `fileConfig(..., disable_existing_loggers=False)`, and only when Alembic is run from the CLI;
  - or remove the logging sections from `alembic.ini`.
- **Verification test:** after lifespan startup, `logging.getLogger("aegis.api.errors").disabled is False`.

### ARCH-4 — High — Confirmed defect — The default CSV mode rejects the project's own dataset format
- **Where:**
  - `backend/services/pipeline.py:938` (`parse_flows_csv`) does not strip or alias headers;
  - the UI default is `frontend/src/pages/DetectionPage.tsx:132` (`useState<CsvMode>("direct")`).
- **Evidence (EXEC):** the first rows of a MachineLearningCVE CSV (headers have leading spaces) give "CSV missing 64 required feature columns" in the direct parser; `ingest_flows_csv` accepts the same bytes.
- **Impact:**
  - Uploading a CICIDS2017 CSV through "Quick score" fails with 422; the same file works in "validated" mode.
  - Two parsers apply different rules to the same feature. ML-13 is the same issue.
- **Remediation:** route `/predict/batch/csv` through `ingestion.pipeline.ingest_flows_csv`.
- **Verification test:** upload a raw MachineLearningCVE header row through every CSV endpoint.

### Medium findings

| ID | Kind | Where (verified) | Evidence | Impact | Remediation / verification |
|---|---|---|---|---|---|
| ARCH-5 | Confirmed defect (EXEC) | `security/response/service.py:359` (`action.status = ActionStatus.VERIFIED.value` is set in memory only) | HTTP response status is VERIFIED; the persisted status is SUCCEEDED. The P6 test accepts SUCCEEDED. | The UI flips to SUCCEEDED on reload. `/ops/status` counts only VERIFIED/ACTIVE, so completed actions vanish from the counts. | Persist after the final transition (and in the failure branches). Tighten the P6 test. |
| ARCH-6 | Confirmed defect (EXEC) | `backend/services/pipeline.py:808` (`row.status = "Simulating"` in an `except ValueError`) | A Resolved incident becomes Simulating and `resolved_at` stays set. | "Simulate" silently reopens closed and false-positive incidents, bypassing `INCIDENT_TRANSITIONS`. | Never assign status outside the state machine. Test: Simulate on a Resolved incident leaves it Resolved. |
| ARCH-7 | Confirmed (READ; batch timing measured) | `backend/routes/api.py:379` (`async def predict_batch_csv`), `:465` (`async def ingest_pcap`) → `ingestion/cicflowmeter_runner.py:39` (`subprocess.run(…, timeout)`, default 300 s); `ws_events` polls analytics every 4 s per client | `async` handlers run CPU and subprocess work inline. FastAPI offloads only `def` handlers. | During PCAP extraction (up to 300 s) the whole process stalls: HTTP, WebSockets and health checks. | Use `def` handlers or `run_in_threadpool`; `asyncio.create_subprocess_exec`; a shared analytics producer. Test: concurrent `/health` latency during a PCAP job. |
| ARCH-8 | Potential risk (READ) | `backend/recovery/startup.py:42` (marks every EXECUTING/APPROVED row FAILED); in-memory queue, range runs, sim sessions, rate limiter, event hub | Latent today because Docker runs one worker; nothing enforces or documents that. | With more than one worker or replica: live actions are marked FAILED, IDs return 404 on other workers, and rate limits multiply by N. | Enforce single-worker, or use lease-based recovery and shared state. |
| ARCH-9 | Confirmed defect (READ) | `ingestion/queue.py:114` (`self._jobs[job.job_id] = job`, never evicted); predict function uses `persist=False` | Only `result_summary` is ever exposed. | Unbounded memory growth. Queue detections never create incidents and cannot be retrieved, so attacks found this way are lost. | TTL eviction; expose results; make persistence configurable. |
| ARCH-10 | Confirmed defect (READ) | `backend/services/pipeline.py:266` (swallow); `backend/observability/health_checks.py:102` (readiness ignores the gate); loader caches failures (`lru_cache`, `_gate_error`) | With `incident_policy: gate` and the gate missing, no incident is ever raised while readiness reports ready. | Silent degradation, e.g. in the Docker image (ARCH-1). | Include the gate in readiness; log and count gate errors; don't cache failures. |
| ARCH-11 | Confirmed defect (READ) | `security/response/service.py:453` `sweep_expired`, called only at startup and from an endpoint with no UI caller; `database/retention.py` `purge_expired`, called only from tests | No scheduler exists. | Time-bound ACTIVE actions never expire while the process runs. The advertised retention policy is never applied. | Add a lifespan background task, or document both as manual. |
| ARCH-12 | Potential risk (READ; probability arithmetic) | `backend/services/pipeline.py:442` (`INC-` + `uuid4().hex[:6]`, 24 bits); unique constraint in `database/db.py` | About a 50 % chance of at least one collision by about 4,800 incidents. There is no retry, and the IntegrityError becomes a 500. | Lost detections; a partially persisted batch. | Longer IDs or a sequence, with retry on IntegrityError. |
| ARCH-13 | Confirmed defect (READ) | `frontend/nginx.conf:9` (no Upgrade/Connection headers); `frontend/src/services/api.ts:1357` (host contains "5173" → `127.0.0.1:8000`) | — | WebSockets work only in local Vite dev. Behind nginx, or from another machine, the Live Monitor and dashboard stream fail. | Add nginx Upgrade headers and Vite `ws: true`; use a same-origin `wsUrl`. |
| ARCH-14 | Confirmed defect (EXEC; precondition: cross-origin deployment) | `backend/main.py:120` (CORS is added first, so it is innermost) | 401 responses have no `Access-Control-Allow-Origin`. | Cross-origin SPA deployments see 401/403/413/429 as "Failed to fetch", so the re-login prompt never appears. | Make CORS the outermost middleware. |
| ARCH-15 | Confirmed (READ) | `.github/workflows/ci.yml:5,7` (`branches: [main, stage2/productionization]`); the docker job only builds | No lint/type check, no migration check, no container start. CI uses Node 20, the Dockerfile Node 22. | The v3 and audit branches get no CI. ARCH-1 passes CI. | Add the branches, a compose smoke job, ruff/mypy and an Alembic check. Keep the frozen-baseline checks read-only. |

### Low and improvement findings

| ID | Kind | Where (verified where a line is given) | Summary / fix |
|---|---|---|---|
| ARCH-16 | Confirmed (EXEC) | `alembic.ini:4` (`script_location = alembic`, relative to the CWD) | Started from another directory, Alembic silently falls back to `create_all` with no `alembic_version` row. Use an absolute path. |
| ARCH-17 | Confirmed (READ, ASGI spec) | `backend/routes/v3.py:113,121` (close 4401 before `accept()`) | Browsers see 1006, so the client's 4401 handling is unreachable and it reconnects forever, writing a security event each time. Accept first, then close with the code. |
| ARCH-18 | **Medium (raised by audit lead)**; Confirmed (READ) | `backend/services/pipeline.py:1125` (`out.write_text`) via `GET /api/models/shap/global?refresh=true` (viewer permission) | A GET by any viewer (anonymous by default) overwrites `models/trained_models/global_shap_summary.json`. **That file is one of the 16 frozen v1.1 files** (`research/artifact_guard.py: FROZEN_V11`; the reviewer's statement that it is not protected was wrong). So one request mutates the frozen baseline; `test_artifact_integrity` would detect this afterwards, but nothing prevents it. Fix: make it a POST, write to a cache directory outside `models/trained_models`, call `assert_writable`, and add a test that the GET never writes. |
| ARCH-19 | Confirmed (READ) | `backend/services/pipeline.py:381` | Same as ML-5: gate-only risk ignores the measured intensity. |
| ARCH-20 | Confirmed (READ) | `cyberrange/engine.py:46` (`RUNS_DIR` inside the repo); `ingestion/cicflowmeter_runner.py:33` (`mkdtemp`, never deleted); sim sessions; rate-limit keys; metric path labels | Unbounded growth. Every UI range run adds an untracked file to the repo. Bound or evict these; delete temp dirs; move RUNS_DIR out of the repo. |
| ARCH-21 | Confirmed (READ) | `backend/services/pipeline.py` `run_prediction_batch` persist branch | Each attack row is re-scored and committed row by row, so a mid-batch failure leaves a partial batch. |
| ARCH-22 | Confirmed (READ) | `backend/middleware/logging_mw.py:26,36` read `state.username/user/role`; auth sets `aegis_user` / `aegis_role` (`api_auth.py:131-132`) | The user never appears in request logs. |
| ARCH-23 | Confirmed (READ) | `security/response/service.py` approve → execute | A pre-execution error leaves the action APPROVED, and the UI has no Execute button, so it is stuck until restart. |
| ARCH-24 | Confirmed (READ) | `frontend/nginx.conf` (no `client_max_body_size`, so nginx defaults to 1 MiB) vs `config.yaml` 25 MiB PCAP limit | Docker uploads over 1 MiB get an nginx HTML 413. |
| ARCH-25 | Confirmed (READ) | `backend/main.py:82` (`ingest_queue.stop()` with `wait=False`; daemon thread) | No graceful drain on shutdown. |
| ARCH-26 | Potential risk (SUSP) | `database/url.py:27` (only `check_same_thread=False`; no WAL, no busy timeout) | Possible `database is locked` under write bursts. Not load-tested. |
| ARCH-27 | Recommendation | auth-enabled flag computed 6 times; WebSocket auth ×2; queue predict function ×2; PCAP handlers ×2; CSV parsers ×2; 4 scenario/replay engines | Consolidate. Mark `simulation/` as a legacy visual demo. |
| ARCH-28 | Recommendation (EXEC import scan, 148 modules) | `api.py` 1,254 LOC, `pipeline.py` 1,200, `api.ts` 1,375, `DetectionPage.tsx` 981 | No top-level import cycles. One lazy cycle: `database.db → bootstrap → security.auth.users → database.db`. Domain modules import the web layer lazily. Split by bounded context. |
| ARCH-29 | Recommendation | Only 2 `response_model`s; `/auth/login` takes `dict`; ignored request fields | Pydantic response models; generate the TypeScript types from OpenAPI. |
| ARCH-30 | Recommendation | Two `scripts/30_*`; legacy paper and replay files in the tree; `ModelVersionRef` seeded with files that aren't served (`database/bootstrap.py`) | Clean up. |

---

## 5. Verified with no defect

- **Alembic vs ORM:** `alembic upgrade head` → `alembic check` reports "No new upgrade operations detected". `downgrade base` and re-upgrade both pass (audit lead, EXEC). The reviewer's `compare_metadata` found 0 diffs.
- **Sessions:** a session is closed after each request, and no leaked sessions were found.
- **Approve/reject races:** handled with an atomic `UPDATE … WHERE status`.
- **Gate singleton:** initialised under a lock.
- **Live Monitor scoring:** runs off the event loop.
