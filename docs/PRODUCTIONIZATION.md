# Aegis IDS — Productionization Roadmap

**Immutable research baseline:** tag `v1.1-research`.  
**Working branch:** `productionization`.

## Phase status

| Phase | Focus | Status |
|-------|--------|--------|
| P0–P6 | Baseline → PCAP → response → adapters → auth → API security → persistence | ✅ |
| **P7** | Observability | ✅ Complete |
| P8 | Performance / load | Next |

## P7 deliverables

- JSON structured operational logs (`aegis.ops`) with correlation fields
- `request_id` / `job_id` / `incident_id` / `action_id` via contextvars
- Domain metrics: API, detection, queue, PCAP, response, security
- `/api/health` = liveness; `/api/ready` = DB + models + filesystem (503 `NOT_READY`, no path leakage)
- `/api/ops/status` + System UI (`/system`) for operator dashboard
- In-process alert thresholds (queue backlog, auth spike, 5xx rate, …)
- Sensitive-field redaction (passwords, tokens, Authorization, api_key)
- Retention notes linking P6 audit retention + process log rotation
- Suite: `tests/test_productionization_p7_observability.py`

**Completion criterion:** an operator can answer what happened, which model/schema handled it, which request/job created it, who acted, how long stages took, and whether response succeeded — via logs + metrics + ops status.

No Prometheus/Grafana/OpenTelemetry in this phase. ML artifacts untouched.
