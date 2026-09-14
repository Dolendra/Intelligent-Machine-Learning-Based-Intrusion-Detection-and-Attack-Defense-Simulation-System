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
| POST | `/api/ingest/pcap` | Offline PCAP via cicflowmeter when installed; else 501 |

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

### Still later

- **D** API hardening + controlled response
- **E** Observability / CI-CD / load tests
- **F** Cyber-range simulation validation + docs


## Safety rules

- Do not retrain or rewrite `models/trained_models/*` as part of ingestion work
- Do not change Stage-1/Stage-2 ML semantics of the research baseline
- Prefer external extractors that emit **MachineLearningCVE-compatible** columns
- TrafficLabelling is **not** a separate training dataset for this project
