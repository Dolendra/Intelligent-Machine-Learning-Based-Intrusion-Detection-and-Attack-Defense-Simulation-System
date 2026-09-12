# Frontend UI/UX

**Stack:** React + TypeScript + Vite + React Flow  
**Brand:** **Aegis IDS**

## Design intent

- One coherent security-ops composition (deep slate, cyan + amber accents)
- Typography: Outfit + IBM Plex Mono (not Inter/Roboto defaults)
- Atmospheric layered backgrounds (not flat white/purple AI chrome)
- Pages each have one job: Dashboard · Detection · Simulation · Reports

## Routes

| Route | Job |
|-------|-----|
| `/` | Incident overview |
| `/detection` | Load demo flow → predict → SHAP |
| `/simulation` | Step through attack/defense on a topology |
| `/reports` | Full incident table + analytics JSON |

Dev proxy: Vite forwards `/api` → `http://127.0.0.1:8000`.
