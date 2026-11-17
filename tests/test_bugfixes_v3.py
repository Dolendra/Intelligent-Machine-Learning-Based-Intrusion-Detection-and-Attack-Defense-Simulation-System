"""Regression tests for bugs found in the v3 UI audit."""
from __future__ import annotations

import asyncio
import threading

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.pipeline import get_predictor

client = TestClient(app)
needs_models = pytest.mark.skipif(get_predictor() is None, reason="trained models not present")


def _attack_flow() -> dict:
    r = client.get("/api/demo/flow", params={"attack_type": "DDoS"})
    assert r.status_code == 200
    return r.json()["features"]


@needs_models
def test_saving_notes_without_changing_status_works():
    """'Save investigation' sends the current status; it used to fail with INVALID_TRANSITION."""
    pred = client.post("/api/predict", json={"features": _attack_flow(), "persist": True}).json()
    iid = pred["incident_id"]
    assert iid
    cur = client.get(f"/api/incidents/{iid}").json()["status"]
    r = client.patch(f"/api/incidents/{iid}", json={"status": cur, "analyst_notes": "checked upstream logs",
                                                    "defense_action": "rate-limit (advisory)"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == cur
    assert body.get("analyst_notes") == "checked upstream logs"


@needs_models
def test_no_campaign_is_invented_without_a_source_reference():
    pred = client.post("/api/predict", json={"features": _attack_flow(), "persist": True}).json()
    assert pred["incident_id"] and pred["campaign_id"] is None


@needs_models
def test_detections_from_one_source_share_a_campaign():
    src = "198.51.100.250"
    flow = _attack_flow()
    a = client.post("/api/predict", json={"features": flow, "persist": True, "source_ref": src}).json()
    b = client.post("/api/predict", json={"features": flow, "persist": True, "source_ref": src}).json()
    assert a["campaign_id"] and a["campaign_id"] == b["campaign_id"]
    camp = client.get(f"/api/campaigns/{a['campaign_id']}").json()
    assert "kill_chain" in camp


@needs_models
def test_demo_flow_is_not_always_the_same_row():
    seen = {tuple(sorted(client.get("/api/demo/flow", params={"attack_type": "DoS"}).json()["features"].items()))
            for _ in range(8)}
    assert len(seen) > 1


def test_notify_sync_from_a_worker_thread_reaches_the_event_loop():
    """Sync request handlers run in worker threads; the broadcast must be scheduled on the WS loop."""
    from backend.services import events

    received: list[dict] = []

    class FakeWS:
        async def send_text(self, payload: str) -> None:
            import json
            received.append(json.loads(payload))

    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()
    hub = events.event_hub
    old_clients, old_loop = list(hub._clients), hub.loop
    try:
        hub._clients[:] = [FakeWS()]
        hub._lock = None
        hub.loop = loop
        done = threading.Event()
        threading.Thread(target=lambda: (events.notify_sync({"type": "incident_created", "incident_id": "X"}), done.set())).start()
        done.wait(2)
        for _ in range(50):
            if received:
                break
            threading.Event().wait(0.02)
        assert received and received[0]["type"] == "incident_created"
    finally:
        hub._clients[:] = old_clients
        hub.loop = old_loop
        hub._lock = None
        loop.call_soon_threadsafe(loop.stop)


def test_incident_listing_respects_a_larger_limit_but_is_capped():
    assert client.get("/api/incidents", params={"limit": 5000}).status_code == 200
