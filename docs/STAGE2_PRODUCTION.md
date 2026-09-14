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
| POST | `/api/response/actions/{id}/approve` | P2: approve → dry execute + verify (no live network) |
| POST | `/api/response/actions/{id}/reject` | P2: reject with audit; no execution |

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

### Phase C — Database + auth/RBAC scaffolding (started)

| Item | Status |
|------|--------|
| SQLite default | unchanged (research baseline) |
| PostgreSQL via `IDS_DB_URL` | URL + pool kwargs ready; install driver separately |
| `/api/security/status` | auth/rate-limit/DB/RBAC summary (public) |
| API key auth | still **disabled by default**; enable `api.auth.enabled` + `AEGIS_API_KEY` |
| RBAC roles | `admin` / `analyst` / `viewer` / `ml_research` via `X-Aegis-Role` |

Not included yet: OAuth/SSO, user tables, password login, full SOC analyst accounts.

### Phase D — API hardening + controlled response (started)

| Item | Status |
|------|--------|
| Rate-limit path coverage | Prefixes include `/api/ingest`, `/api/response`, `/api/simulation`, … (still **off** by default) |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-Aegis-Live-Mitigation: false` |
| `POST /api/response/plan` | Advisory playbook + optional simulation preview |
| Live mitigation | **Not implemented** — response remains decision-support / sim |

Honest limits: no firewall/WAF/agent connectors; `defense_action` on incidents is an analyst note, not an executed control.

### Phase E — Observability / CI-CD / load tests (started)

| Item | Status |
|------|--------|
| `GET /api/metrics` | In-process request counters + p50/p95 latency samples |
| Request logging | Existing `StructuredLoggingMiddleware` + `X-Request-ID` |
| Load smoke | `python scripts/26_api_load_smoke.py` (health/ready/metrics only) |
| CI | Runs on `main` **and** `stage2/productionization`; `stage2-gate` job |
| Docker image | `Dockerfile.api` copies `ingestion/` for Stage-2 APIs |

Honest limits: **not** Prometheus/Grafana/OpenTelemetry; metrics reset on process restart; load smoke is **not** a capacity/SLA claim.

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
