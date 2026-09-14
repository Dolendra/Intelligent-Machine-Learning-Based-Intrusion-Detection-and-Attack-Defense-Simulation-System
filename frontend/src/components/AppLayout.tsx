import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../services/api";

const NAV = [
  { to: "/", end: true, label: "Dashboard", ico: "01", section: "Operations" },
  { to: "/detection", label: "Detection", ico: "02", section: "Operations" },
  { to: "/simulation", label: "Simulation", ico: "03", section: "Operations" },
  { to: "/reports", label: "Reports", ico: "04", section: "Investigate" },
  { to: "/campaigns", label: "Campaigns", ico: "05", section: "Investigate" },
  { to: "/models", label: "Models", ico: "06", section: "Lab" },
  { to: "/research", label: "Research", ico: "07", section: "Lab" },
] as const;

export function AppLayout() {
  const [modelsLoaded, setModelsLoaded] = useState<boolean | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) => setModelsLoaded(h.models_loaded))
      .catch(() => setModelsLoaded(false));
  }, []);

  let lastSection = "";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-shield" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <path d="M12 3l7 3v5c0 4.5-2.8 7.8-7 10-4.2-2.2-7-5.5-7-10V6l7-3z" />
              <path d="M9.2 12.2l1.9 1.9 3.8-4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="brand-mark">Aegis</div>
          <h1>IDS Platform</h1>
          <p>Detect · Explain · Recommend · Simulate</p>
        </div>

        <nav className="nav" aria-label="Primary">
          {NAV.map((item) => {
            const showSection = item.section !== lastSection;
            lastSection = item.section;
            return (
              <div key={item.to}>
                {showSection && <div className="nav-section">{item.section}</div>}
                <NavLink to={item.to} end={"end" in item ? item.end : undefined}>
                  <span className="nav-ico">{item.ico}</span>
                  {item.label}
                </NavLink>
              </div>
            );
          })}
        </nav>

        <div className="sidebar-foot">
          <div className="status-pill">
            <span className={`status-dot ${modelsLoaded ? "on" : ""}`} />
            {modelsLoaded === null
              ? "Checking models…"
              : modelsLoaded
                ? "Models online"
                : "Models offline"}
          </div>
          {modelsLoaded === false && (
            <p className="muted" style={{ fontSize: "0.78rem", margin: "0 0.35rem", lineHeight: 1.35 }}>
              Start API: <span className="mono">uvicorn backend.main:app --port 8000</span>
              <br />
              Train if needed: <span className="mono">scripts/02_train_models.py</span>
            </p>
          )}
        </div>
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
