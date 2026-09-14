# Aegis IDS — Productionization Roadmap

**Immutable research baseline:** tag `v1.1-research`.  
**Working branch:** `productionization`.

## Phase status

| Phase | Focus | Status |
|-------|--------|--------|
| P0–P4 | Baseline → PCAP → response → adapters → auth/RBAC | ✅ |
| **P5** | API + application security | ✅ Complete |
| P6 | Persistence | Next |

## P5 deliverables

- Rate limiting **ON by default** for `/api/auth/login`, predict, ingest, response, …
- Prefix-bucketed limits (blocks trivial path-variant bypass)
- Stricter login limit (`10/60s`)
- Request-size limits (JSON/CSV/PCAP/multipart) via Content-Length
- PCAP filename path-traversal rejection + safe temp suffixes
- Sanitized validation/500 errors (no stack/secret/`input` leakage)
- CORS allowlist; optional `AEGIS_CORS_STRICT` for production headers/methods
- WebSocket `/api/ws/events` auth when `AEGIS_AUTH_ENABLED=true`
- Security event logging for rate-limit / oversized / WS deny
- Dedicated suite: `tests/test_productionization_p5_security.py`

**Completion criterion:** malicious or unauthorized requests are rejected at the application boundary before sensitive business logic / response adapters, with auditable security events.

CI uses `DISABLE_RATE_LIMIT=true` for deterministic functional tests. ML artifacts untouched.
