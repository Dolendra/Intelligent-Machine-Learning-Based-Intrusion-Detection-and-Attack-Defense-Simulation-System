"""Stage-2 productionization roadmap (branch work — does not replace v1.1 baseline)."""

# Aegis IDS — Stage 2 Productionization

## Framing

| Track | Meaning |
|-------|---------|
| **v1.1 research baseline** | Frozen academic/demo prototype (`main` / tag-worthy commits around `7ca09c2`+) |
| **Stage 2** | Productionization on branch `stage2/productionization` |

Do **not** claim live capture, automatic mitigation, or OAuth SSO until those pieces are implemented and validated.

## Phase A — Foundation (this branch)

1. **Feature schema versioning** — `ingestion/schema/cicids2017_v1_1.json` + `/api/ingest/capabilities`
2. **CSV flow ingestion adapter** — align MachineLearningCVE-compatible CSVs to the frozen 78-feature schema
3. **Column alias normalization** — map common CICFlowMeter abbreviations (`Dst Port`, `Tot Fwd Pkts`, …) onto the frozen schema
4. **Optional CICFlowMeter PCAP path** — when `cicflowmeter` is on PATH: extract → normalize → validate → optional predict
5. **CLI** — `python -m ingestion capabilities|schema|normalize-csv|pcap|ingest-csv`

### New API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/ingest/capabilities` | Schema version + extractor status |
| POST | `/api/ingest/flows/csv` | Offline CSV → validated feature rows (+ optional predict) |
| POST | `/api/ingest/pcap` | Offline PCAP (P1: size/magic/extension validation + audit); cicflowmeter when installed; else 501 |
| POST | `/api/ingest/queue/submit-pcap` | Same detect queue as CSV after PCAP→flow extract; 501 without cicflowmeter |
| POST | `/api/response/actions/propose` | P2: propose abstract DRY_RUN action (pending approval) |
| POST | `/api/response/actions/{id}/approve` | Approve → adapter execute + verify (DRY_RUN or CONTROLLED) |
| POST | `/api/response/actions/{id}/reject` | Reject with audit; no execution |
| POST | `/api/response/actions/{id}/rollback` | P3: reverse reversible actions via adapter |
| GET | `/api/response/adapters` | dry_run / test_network / live_forbidden (live disabled) |

> **Productionization (post `v1.1-research`):** see `docs/PRODUCTIONIZATION.md`. Branch `productionization` hardens offline PCAP (P1) and adds dry-run/approval response gate (P2) without changing frozen DT/RF artifacts. Live NIC capture and live firewall/EDR adapters remain out of scope until later phases.

### CLI examples

```bash
python -m ingestion capabilities
python -m ingestion normalize-csv -i flows.csv -o aligned.csv
python -m ingestion pcap -i capture.pcap --align
```


## Later phases

### Phase B — Real-time / batch detection path (started)

In-process FIFO queue (single API worker):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/ingest/queue` | Queue depth + latency / throughput metrics |
| POST | `/api/ingest/queue/submit` | Enqueue validated CSV flows for async detect |
| GET | `/api/ingest/queue/{job_id}` | Poll job status / summary |

Honest limits: **not** Redis/Kafka, **not** multi-node. Useful for staging batches and measuring detect latency on one process.

### Phase C — Database + auth/RBAC (P4 complete on `productionization`)

| Item | Status |
|------|--------|
| SQLite default | unchanged (research baseline) |
| PostgreSQL via `IDS_DB_URL` | URL + pool kwargs ready; install driver separately |
| `/api/security/status` | auth/rate-limit/DB/RBAC/request-limits summary (public) |
| Password login + Bearer tokens | P4 — enable `AEGIS_AUTH_ENABLED=true` |
| Server RBAC | Roles from directory/token; forged body/header ignored |
| API key auth | optional alongside Bearer; still off unless enabled |

Not included yet: OAuth/SSO. Persistence of users/actions across restarts is **P6** (complete on `productionization`).

### Phase D — API hardening (P5 complete on `productionization`)

| Item | Status |
|------|--------|
| Rate limiting | **ON by default** for login/predict/ingest/response/… (`DISABLE_RATE_LIMIT` for CI) |
| Request-size limits | JSON/CSV/PCAP/multipart Content-Length caps |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, … |
| Error sanitization | No stack/`input`/secret leakage; correlation `request_id` |
| WebSocket auth | `/api/ws/events` requires Bearer/token when auth enabled |
| Upload safety | Basename-only filenames; PCAP magic/size/extension |
| `POST /api/response/plan` | Advisory playbook + optional simulation preview |
| Live mitigation | **Not implemented** — response remains decision-support / controlled dry-run |

Honest limits: no firewall/WAF/agent connectors; in-process rate limits (not Redis); CORS remains localhost allowlist unless `AEGIS_CORS_STRICT`.

### Phase persistence (P6 complete on `productionization`)

| Item | Status |
|------|--------|
| Alembic `002_p6_persistence` | users, response_actions, response/security audit, model refs |
| Response store | DB-backed; append-only audit; atomic approve/reject |
| Users | Durable seed directory |
| Retention | Documented in `database.retention` (not silent audit wipe) |
| Restart tests | `tests/test_productionization_p6_persistence.py` |

Ephemeral by design: ingest queue, WS clients, rate-limit counters. Full backup/DR is P9.

### Phase E — Observability (P7) + Performance (P8)

| Item | Status |
|------|--------|
| Structured JSON logs + correlation | P7 |
| `/api/ops/status` + System UI | P7 |
| Performance harness | `performance/` + `scripts/30–37_*` |
| Operating envelope | `docs/PERFORMANCE.md`, `results/performance/operating_envelope_latest.json` |
| CI | Fast functional only; benches are manual/local |

Honest limits: single-process measurements; not multi-node capacity or SLA.

### Phase F — Cyber-range simulation validation + docs (started)

| Item | Status |
|------|--------|
| Validation module | `simulation/validation.py` — lifecycle + advisory framing checks |
| CLI | `python scripts/27_cyber_range_sim_validate.py` |
| Families covered | DDoS, DoS, PortScan, BruteForce, WebAttack, Bot |
| Efficacy table | From `config.yaml` `simulation.defense_effectiveness` (**assumptions**) |
| CI | Included in `stage2-gate` |

Honest limits: **not** a physical cyber range; **not** measured real-world mitigation rates; simulation timings are deterministic visualization clocks.

### Stage-2 complete (branch scaffolding)

Phases A–F on `stage2/productionization` provide productionization scaffolding on top of the v1.1 research baseline. Merge to `main` only when intentionally promoting Stage-2.


## Safety rules

- Do not retrain or rewrite `models/trained_models/*` as part of ingestion work
- Do not change Stage-1/Stage-2 ML semantics of the research baseline
- Prefer external extractors that emit **MachineLearningCVE-compatible** columns
- TrafficLabelling is **not** a separate training dataset for this project
