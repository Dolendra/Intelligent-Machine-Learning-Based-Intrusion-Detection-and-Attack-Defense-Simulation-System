"""End-to-end smoke test of the Aegis demo path (no UI required)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services.pipeline import load_demo_flow, models_ready, run_explain, run_prediction
from database.db import SessionLocal, init_db
from security.recommendations.engine import recommend
from simulation.engine.core import SimulationEngine


def main() -> int:
    print("1) Models loaded?", models_ready())
    if not models_ready():
        print("FAIL: train models first")
        return 1

    init_db()
    demo = load_demo_flow("DDoS")
    print("2) Demo ground truth:", demo["label"])

    db = SessionLocal()
    try:
        pred = run_prediction(demo["features"], db=db, persist=True)
    finally:
        db.close()
    print(
        f"3) Predict: {pred['attack_type']} "
        f"conf={pred['confidence']:.3f} risk={pred['risk_score']} {pred['severity']} "
        f"incident={pred['incident_id']}"
    )
    assert pred["is_attack"], "expected attack on DDoS sample"

    shap = run_explain(demo["features"], top_k=5, method="shap")
    lime = run_explain(demo["features"], top_k=5, method="lime")
    print("4) SHAP top:", [f["feature"] for f in shap["top_features"][:3]])
    print("   LIME top:", [f["feature"] for f in lime["top_features"][:3]])

    rec = recommend(pred["attack_type"], pred["severity"])
    print("5) Recommendation:", rec["primary"])

    sim = SimulationEngine()
    session = sim.start(pred["attack_type"], pred["confidence"])
    states = [session["state"]]
    for _ in range(7):
        session = sim.advance(session["id"])
        states.append(session["state"])
    print("6) Simulation states:", " -> ".join(states))
    assert "detected" in states and states[-1] == "recovered"

    print("\nSMOKE OK - demo path works.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
