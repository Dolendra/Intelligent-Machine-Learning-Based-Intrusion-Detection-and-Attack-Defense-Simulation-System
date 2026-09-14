# Frontend UI/UX

**Stack:** React + TypeScript + Vite + React Flow  
**Brand:** **Aegis IDS**

## Design intent

- One coherent security-ops composition (deep slate, cyan + amber accents)
- Typography: Outfit + IBM Plex Mono (not Inter/Roboto defaults)
- Atmospheric layered backgrounds (not flat white/purple AI chrome)
- Each page has one primary job

## Routes

| Route | Page | Job |
|-------|------|-----|
| `/` | Dashboard | KPIs, recent incidents, attack / risk overview |
| `/detection` | Detection | Demo / CSV / Stage-2 ingest → predict → SHAP → risk → recommendation |
| `/simulation` | Simulation | Attack→defense lifecycle on a topology (visualization only) |
| `/reports` | Reports | Incident table, analytics JSON/PDF export |
| `/campaigns` | Campaigns | Correlated multi-step attack campaigns / kill-chain view |
| `/incidents/:id` | Incident detail | Lifecycle status, notes, defense_action (advisory note) |
| `/models` | Models | Model versions, metrics, comparison |
| `/research` | Research | Experiments, temporal/drift methodology notes |

Dev proxy: Vite forwards `/api` → `http://127.0.0.1:8000`.
