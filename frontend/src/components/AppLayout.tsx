import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../services/api";

export function AppLayout() {
  const [modelsLoaded, setModelsLoaded] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) => setModelsLoaded(h.models_loaded))
      .catch(() => setModelsLoaded(false));
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">Aegis</div>
          <h1>IDS Platform</h1>
          <p>Detect · Explain · Recommend · Simulate</p>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/detection">Detection</NavLink>
          <NavLink to="/simulation">Simulation</NavLink>
          <NavLink to="/reports">Reports</NavLink>
          <NavLink to="/models">Models</NavLink>
        </nav>
        <div className="status-pill" style={{ marginTop: "auto" }}>
          <span className={`status-dot ${modelsLoaded ? "on" : ""}`} />
          {modelsLoaded === null ? "Checking models…" : modelsLoaded ? "Models online" : "Models offline"}
        </div>
        {modelsLoaded === false && (
          <p className="muted" style={{ fontSize: "0.78rem", margin: "0.5rem 0.35rem 0", lineHeight: 1.35 }}>
            Start API: <span className="mono">uvicorn backend.main:app --port 8000</span>
            <br />
            Train if needed: <span className="mono">scripts/02_train_models.py</span>
          </p>
        )}
      </aside>
      <main className="main">
        {modelsLoaded === false && (
          <div
            className="panel rise"
            style={{ marginBottom: "1rem", borderColor: "rgba(228,165,74,.45)", background: "var(--amber-dim)" }}
          >
            <strong>Backend offline or models missing.</strong>
            <span className="muted"> Detection and explainability need the FastAPI server with trained artifacts.</span>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
