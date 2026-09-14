# Aegis IDS — Productionization Roadmap

**Immutable research baseline:** tag `v1.1-research` (Decision Tree @ 0.85 + Random Forest attack-only).  
**Working branch:** `productionization` (extends `main`; never rewrite freeze artifacts under `models/trained_models/`).

## Positioning

| Claim | OK? |
|-------|-----|
| Submission-ready / productionized **IDS prototype** | ✅ |
| Live enterprise SOC / guaranteed zero-day / auto-block | ❌ |

## Phase status

| Phase | Focus | Status |
|-------|--------|--------|
| **P0** | Freeze `v1.1-research` | ✅ |
| **P1** | PCAP → queue → frozen DT/RF | ✅ |
| **P2** | Dry-run + approval gate | ✅ |
| **P3** | Adapters + verify + rollback | ✅ |
| **P4** | Authentication / RBAC | ✅ Complete (this branch) |
| **P5** | API + application security | Next |

## P4 deliverables

```text
User → login (PBKDF2 password) → HMAC Bearer token → role from user directory
     → server-side RBAC on every sensitive route → audit actor = username
```

| Role | Propose/dry-run | Approve/rollback | Manage users |
|------|----------------:|-----------------:|-------------:|
| Viewer | ❌ | ❌ | ❌ |
| Analyst | ✅ | ❌ | ❌ |
| Responder | ✅ | ✅ | ❌ |
| Admin | ✅ | ✅ | ✅ |

- **401** unauthenticated; **403** authenticated but forbidden  
- Client `X-Aegis-Role` cannot escalate unless `allow_role_header=true` (demo only)  
- UI reflects permissions; **API is the security boundary**  
- Auth remains **off by default** for the research demo; enable with `AEGIS_AUTH_ENABLED=true`

## Safety invariants preserved

No approval → no execution · DRY_RUN/CONTROLLED only · LIVE forbidden · unauthorized → no response action · audit identity bound to login
