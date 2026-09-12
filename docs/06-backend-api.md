# Backend API

**Entrypoint:** `uvicorn backend.main:app --reload --port 8000`  
**OpenAPI:** http://localhost:8000/docs

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Liveness + model status |
| POST | `/api/predict` | Detect + classify + risk + recommend |
| POST | `/api/explain` | SHAP explanation |
| POST | `/api/risk` | Standalone risk score |
| POST | `/api/recommendation` | Standalone advice |
| POST | `/api/simulation/start` | New scenario |
| POST | `/api/simulation/advance` | Step / defend / reset |
| GET | `/api/incidents` | Incident list |
| GET | `/api/analytics` | Aggregates |
| GET | `/api/demo/flow` | Sample CICIDS row |
| GET | `/api/features/template` | Zeroed feature map |

SQLite DB: `database/ids.db` (auto-created on startup).
