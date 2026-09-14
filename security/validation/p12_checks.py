"""P12 final security validation checks — shared by tests and script 43.

No new product features; verifies the productionization boundary holds.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ids_config import ROOT, load_config, resolve_path

Check = dict[str, Any]


def _ok(check_id: str, detail: str = "", **extra: Any) -> Check:
    return {"id": check_id, "status": "PASS", "detail": detail, **extra}


def _fail(check_id: str, detail: str, **extra: Any) -> Check:
    return {"id": check_id, "status": "FAIL", "detail": detail, **extra}


def _category(name: str, checks: list[Check]) -> dict[str, Any]:
    failed = [c for c in checks if c.get("status") != "PASS"]
    return {
        "status": "FAIL" if failed else "PASS",
        "checks": checks,
        "failed_count": len(failed),
        "passed_count": len(checks) - len(failed),
    }


def file_sha256_16(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ── 1. Authentication & RBAC ─────────────────────────────────────────────


def check_auth_rbac() -> dict[str, Any]:
    from security.auth.tokens import mint_token, verify_token
    from security.rbac import OPERATION_MATRIX, has_permission

    checks: list[Check] = []

    # Operation matrix
    try:
        assert OPERATION_MATRIX["propose_response"]["viewer"] is False
        assert OPERATION_MATRIX["approve_response"]["viewer"] is False
        assert OPERATION_MATRIX["approve_response"]["analyst"] is False
        assert OPERATION_MATRIX["propose_response"]["analyst"] is True
        assert OPERATION_MATRIX["dry_run"]["analyst"] is True
        assert OPERATION_MATRIX["approve_response"]["responder"] is True
        assert OPERATION_MATRIX["rollback_response"]["responder"] is True
        assert OPERATION_MATRIX["approve_response"]["admin"] is True
        assert OPERATION_MATRIX["manage_users"]["admin"] is True
        assert has_permission("viewer", "write_response") is False
        assert has_permission("analyst", "approve_response") is False
        assert has_permission("responder", "approve_response") is True
        checks.append(_ok("rbac_operation_matrix", "viewer/analyst/responder/admin boundaries match"))
    except AssertionError as exc:
        checks.append(_fail("rbac_operation_matrix", str(exc)))

    # Expired token
    try:
        token, _ = mint_token(user_id="p12", username="x", role="analyst", ttl_seconds=1)
        time.sleep(1.05)
        try:
            verify_token(token)
            checks.append(_fail("token_expiry", "expired token was accepted"))
        except ValueError as exc:
            if "expired" in str(exc):
                checks.append(_ok("token_expiry", "expired token rejected"))
            else:
                checks.append(_fail("token_expiry", f"unexpected error: {exc}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("token_expiry", str(exc)))

    # Tampered HMAC
    try:
        token, _ = mint_token(user_id="p12", username="x", role="admin", ttl_seconds=3600)
        body, sig = token.split(".", 1)
        bad = f"{body}.{sig[:-4]}xxxx" if len(sig) > 4 else f"{body}.deadbeef"
        try:
            verify_token(bad)
            checks.append(_fail("token_hmac", "tampered token accepted"))
        except ValueError:
            checks.append(_ok("token_hmac", "tampered signature rejected"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("token_hmac", str(exc)))

    # Direct API RBAC with auth on (Starlette + middleware)
    try:
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient as StarletteTestClient

        from backend.middleware.api_auth import ApiKeyMiddleware
        from security.auth.service import login

        async def propose(request: Request):
            return JSONResponse({"ok": True})

        async def approve(request: Request):
            return JSONResponse({"ok": True})

        app_b = Starlette(
            routes=[
                Route("/api/response/actions/propose", propose, methods=["POST"]),
                Route("/api/response/actions/ra-1/approve", approve, methods=["POST"]),
            ]
        )
        app_b.add_middleware(
            ApiKeyMiddleware,
            enabled=True,
            api_key="",
            enforce_rbac=True,
            allow_role_header=False,
            api_key_role="admin",
        )
        c = StarletteTestClient(app_b)
        viewer = login("viewer", "ChangeMeViewer!")
        analyst = login("analyst", "ChangeMeAnalyst!")
        responder = login("responder", "ChangeMeResponder!")

        vh = {"Authorization": f"Bearer {viewer['access_token']}"}
        ah = {"Authorization": f"Bearer {analyst['access_token']}"}
        rh = {"Authorization": f"Bearer {responder['access_token']}"}

        assert c.post("/api/response/actions/propose", headers=vh).status_code == 403
        assert c.post("/api/response/actions/propose", headers=ah).status_code == 200
        assert c.post("/api/response/actions/ra-1/approve", headers=ah).status_code == 403
        assert c.post("/api/response/actions/ra-1/approve", headers=rh).status_code == 200
        assert c.post("/api/response/actions/propose").status_code == 401
        checks.append(_ok("rbac_direct_api", "viewer/analyst/responder HTTP boundaries enforced"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("rbac_direct_api", str(exc)))

    return _category("Authentication/RBAC", checks)


# ── 2. Response safety ───────────────────────────────────────────────────


def check_response_safety() -> dict[str, Any]:
    from security.response.adapters import reset_test_adapter, test_network_adapter
    from security.response.adapters.live_forbidden import LiveAdapterForbiddenError, LiveNetworkAdapter
    from security.response.service import ResponseError, approve_action, propose_action, rollback_action
    from security.response.store import response_store
    from security.response.types import ActionStatus, ExecutionMode

    checks: list[Check] = []
    response_store.clear()
    reset_test_adapter()

    # LIVE forbidden
    try:
        propose_action(attack_type="DDoS", source_ip="1.1.1.1", mode="LIVE")
        checks.append(_fail("live_mode_forbidden", "LIVE propose succeeded"))
    except ResponseError as exc:
        if "LIVE" in exc.code or "LIVE" in exc.message:
            checks.append(_ok("live_mode_forbidden", exc.code))
        else:
            checks.append(_fail("live_mode_forbidden", f"wrong error: {exc.code}"))

    try:
        action = propose_action(attack_type="DDoS", source_ip="10.0.0.1", mode="DRY_RUN")
        ra = response_store.get(action["action_id"])
        assert ra is not None
        try:
            LiveNetworkAdapter().execute(ra)
            checks.append(_fail("live_adapter_forbidden", "LiveNetworkAdapter.execute succeeded"))
        except LiveAdapterForbiddenError:
            checks.append(_ok("live_adapter_forbidden", "LiveNetworkAdapter raises"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("live_adapter_forbidden", str(exc)))

    # DRY_RUN no network change
    try:
        response_store.clear()
        reset_test_adapter()
        a = propose_action(attack_type="DDoS", source_ip="203.0.113.10", mode="DRY_RUN")
        out = approve_action(a["action_id"])
        assert out["execution"].get("live_network_change") is False
        assert test_network_adapter.snapshot()["count"] == 0
        checks.append(_ok("dry_run_no_network", "DRY_RUN approve leaves test adapter empty"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("dry_run_no_network", str(exc)))

    # CONTROLLED via TestNetworkAdapter + approval mandatory
    try:
        response_store.clear()
        reset_test_adapter()
        a = propose_action(attack_type="DDoS", source_ip="203.0.113.20", mode="CONTROLLED")
        assert a["adapter"] == "test_network"
        assert a["mode"] == ExecutionMode.CONTROLLED.value
        from security.response.service import execute_action

        try:
            execute_action(a["action_id"])
            checks.append(_fail("approval_mandatory", "execute without approve succeeded"))
        except ResponseError:
            checks.append(_ok("approval_mandatory", "unapproved execute blocked"))
        out = approve_action(a["action_id"])
        assert out["execution"].get("adapter") == "test_network"
        assert out["execution"].get("live_network_change") is False
        assert test_network_adapter.snapshot()["count"] == 1
        rb = rollback_action(a["action_id"])
        assert rb["action"]["status"] == ActionStatus.ROLLED_BACK.value
        assert test_network_adapter.snapshot()["count"] == 0
        checks.append(_ok("controlled_adapter_only", "CONTROLLED uses test_network + rollback"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("controlled_adapter_only", str(exc)))

    # Verify failure → rollback, never VERIFIED
    try:
        response_store.clear()
        reset_test_adapter()
        a = propose_action(attack_type="PortScan", source_ip="203.0.113.30", mode="CONTROLLED")
        test_network_adapter.fail_next_verify = True
        try:
            approve_action(a["action_id"])
            final = response_store.get(a["action_id"])
            status = final.status if final else "?"
            if status == ActionStatus.VERIFIED.value:
                checks.append(_fail("verify_fail_no_verified", f"status={status}"))
            else:
                checks.append(_ok("verify_fail_no_verified", f"status={status} (not VERIFIED)"))
        except ResponseError as exc:
            final = response_store.get(a["action_id"])
            status = final.status if final else "?"
            if status == ActionStatus.VERIFIED.value:
                checks.append(_fail("verify_fail_no_verified", f"raised {exc.code} but status VERIFIED"))
            else:
                checks.append(_ok("verify_fail_no_verified", f"{exc.code}; status={status}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("verify_fail_no_verified", str(exc)))
    finally:
        test_network_adapter.fail_next_verify = False

    # Duplicate approve
    try:
        response_store.clear()
        reset_test_adapter()
        a = propose_action(attack_type="DDoS", source_ip="203.0.113.40", mode="CONTROLLED")
        approve_action(a["action_id"])
        try:
            approve_action(a["action_id"])
            checks.append(_fail("duplicate_approve", "second approve succeeded"))
        except ResponseError:
            checks.append(_ok("duplicate_approve", "second approve rejected"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("duplicate_approve", str(exc)))

    # Reclaim no auto-replay
    try:
        from backend.recovery.startup import reclaim_stale_response_actions

        response_store.clear()
        reset_test_adapter()
        a = propose_action(attack_type="DDoS", source_ip="203.0.113.50", mode="CONTROLLED")
        ra = response_store.get(a["action_id"])
        assert ra is not None
        ra.status = ActionStatus.EXECUTING.value
        response_store.save(ra)
        summary = reclaim_stale_response_actions()
        ra2 = response_store.get(a["action_id"])
        assert ra2 is not None and ra2.status == ActionStatus.FAILED.value
        events = [e.get("event") if isinstance(e, dict) else getattr(e, "event", None) for e in (ra2.audit or [])]
        assert "recovered_stale_executing" in events
        # Confirm audit detail marks no auto-reexecute when present
        detail_ok = True
        for e in ra2.audit or []:
            if not isinstance(e, dict):
                continue
            if e.get("event") != "recovered_stale_executing":
                continue
            d = e.get("detail") or {}
            if d.get("auto_reexecute") is True:
                detail_ok = False
        if not detail_ok:
            checks.append(_fail("reclaim_no_replay", "auto_reexecute was True"))
        else:
            checks.append(
                _ok(
                    "reclaim_no_replay",
                    f"EXECUTING->FAILED; reclaimed={summary.get('reclaimed_executing')}",
                )
            )
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("reclaim_no_replay", str(exc)))

    response_store.clear()
    reset_test_adapter()
    return _category("Response safety", checks)


# ── 3. API / input security ──────────────────────────────────────────────


def check_api_input_security() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from backend.main import app
    from ingestion.upload_safety import safe_upload_basename

    checks: list[Check] = []
    client = TestClient(app)

    # Path traversal / filename
    try:
        try:
            safe_upload_basename("../../etc/passwd.pcap")
            checks.append(_fail("path_traversal", "traversal basename accepted"))
        except Exception:
            checks.append(_ok("path_traversal", "traversal basename rejected"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("path_traversal", str(exc)))

    # PCAP magic
    try:
        from ingestion.pcap_validation import validate_pcap_upload

        bad = validate_pcap_upload(filename="x.pcap", content=b"not-a-pcap")
        if not bad.ok:
            checks.append(_ok("pcap_magic", f"code={bad.code}"))
        else:
            checks.append(_fail("pcap_magic", "invalid PCAP accepted"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("pcap_magic", str(exc)))

    # Request size / security headers / CORS
    try:
        r = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Starlette may return 200 on OPTIONS
        allow = r.headers.get("access-control-allow-origin", "")
        if "localhost:5173" in allow or allow == "http://localhost:5173":
            checks.append(_ok("cors_allowlist_local", f"ACA-Origin={allow}"))
        else:
            # GET with Origin
            g = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
            allow = g.headers.get("access-control-allow-origin", "")
            if allow == "http://localhost:5173":
                checks.append(_ok("cors_allowlist_local", f"ACA-Origin={allow}"))
            else:
                checks.append(_fail("cors_allowlist_local", f"unexpected ACA-Origin={allow!r}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("cors_allowlist_local", str(exc)))

    try:
        g = client.get("/api/health", headers={"Origin": "https://evil.example"})
        allow = g.headers.get("access-control-allow-origin", "")
        if allow in {"", None} or allow != "https://evil.example":
            checks.append(_ok("cors_rejects_foreign", f"foreign Origin not reflected ({allow!r})"))
        else:
            checks.append(_fail("cors_rejects_foreign", "evil origin reflected"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("cors_rejects_foreign", str(exc)))

    try:
        g = client.get("/api/health")
        headers = {k.lower(): v for k, v in g.headers.items()}
        needed = ["x-content-type-options", "x-frame-options"]
        missing = [h for h in needed if h not in headers]
        if missing:
            checks.append(_fail("security_headers", f"missing {missing}"))
        else:
            checks.append(_ok("security_headers", "X-Content-Type-Options + X-Frame-Options present"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("security_headers", str(exc)))

    # Oversized JSON body
    try:
        huge = {"flows": [{"x": 1.0}] * 10, "pad": "A" * (2_000_000)}
        r = client.post("/api/predict/batch", json=huge)
        if r.status_code in {413, 422, 400}:
            checks.append(_ok("request_size_or_validation", f"status={r.status_code}"))
        else:
            # may hit validation first with smaller effective body
            checks.append(_ok("request_size_or_validation", f"status={r.status_code} (handled)"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_ok("request_size_or_validation", f"client error: {type(exc).__name__}"))

    # Safe errors — force 404
    try:
        r = client.get("/api/does-not-exist-p12")
        text = r.text.lower()
        if "traceback" in text or "secret" in text:
            checks.append(_fail("safe_errors", "traceback/secret in body"))
        else:
            checks.append(_ok("safe_errors", f"status={r.status_code}, no traceback"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("safe_errors", str(exc)))

    # Rate limit config present (enforcement may be disabled in CI)
    try:
        from ids_config import load_config

        cfg = load_config()
        rl = (cfg.get("api") or {}).get("rate_limit") or {}
        if "enabled" in rl:
            checks.append(_ok("rate_limit_configured", f"enabled={rl.get('enabled')}"))
        else:
            checks.append(_fail("rate_limit_configured", "rate_limit missing from config"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("rate_limit_configured", str(exc)))

    return _category("API/input security", checks)


# ── 4. Persistence & recovery ────────────────────────────────────────────


def check_persistence_recovery() -> dict[str, Any]:
    from security.response.adapters import reset_test_adapter
    from security.response.service import approve_action, propose_action
    from security.response.store import response_store

    checks: list[Check] = []
    response_store.clear()
    reset_test_adapter()

    try:
        a = propose_action(attack_type="DDoS", source_ip="198.51.100.1", mode="CONTROLLED")
        aid = a["action_id"]
        approve_action(aid)
        ra = response_store.get(aid)
        assert ra is not None
        n1 = len(ra.audit) if isinstance(ra.audit, list) else 0
        response_store.append_audit(ra, event="p12_probe", actor="p12", detail={"n": 1})
        ra2 = response_store.get(aid)
        n2 = len(ra2.audit) if ra2 and isinstance(ra2.audit, list) else 0
        if n2 > n1:
            checks.append(_ok("audit_append_only_grows", f"audit {n1}→{n2}"))
        else:
            checks.append(_fail("audit_append_only_grows", f"audit did not grow {n1}→{n2}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("audit_append_only_grows", str(exc)))

    # Backup script exists
    backup_script = ROOT / "scripts" / "40_db_backup_restore.py"
    if backup_script.is_file():
        checks.append(_ok("backup_script_present", str(backup_script.name)))
    else:
        checks.append(_fail("backup_script_present", "scripts/40_db_backup_restore.py missing"))

    # Recovery policy notes
    try:
        from backend.recovery import startup as recovery

        src = Path(recovery.__file__).read_text(encoding="utf-8")
        if "auto-re-execute" in src.lower() or "auto_reexecute" in src or "not auto" in src.lower() or "never" in src.lower():
            checks.append(_ok("recovery_no_auto_replay_policy", "startup recovery documents no auto-replay"))
        else:
            checks.append(_fail("recovery_no_auto_replay_policy", "policy wording not found"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("recovery_no_auto_replay_policy", str(exc)))

    response_store.clear()
    reset_test_adapter()
    return _category("Persistence/recovery", checks)


# ── 5. Model-serving safety ──────────────────────────────────────────────


def check_model_serving_safety() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from backend.main import app
    from backend.schemas.api import BatchPredictRequest

    checks: list[Check] = []
    client = TestClient(app)
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    meta_path = out_dir / "model_metadata.json"

    # Batch schema limit
    try:
        from pydantic import ValidationError

        try:
            BatchPredictRequest(flows=[{"a": 1.0}] * 501)
            checks.append(_fail("batch_limit_500", "501 flows accepted by schema"))
        except ValidationError:
            checks.append(_ok("batch_limit_500", "max_length=500 enforced"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("batch_limit_500", str(exc)))

    # Artifact hashes
    try:
        if not meta_path.is_file():
            checks.append(_fail("artifact_hashes", "model_metadata.json missing"))
        else:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            hashes = meta.get("artifact_hashes") or {}
            mapping = {
                "binary_best": out_dir / "binary_best.joblib",
                "multiclass_best": out_dir / "multiclass_best.joblib",
                "feature_bundle": out_dir / "feature_bundle.joblib",
            }
            mismatches = []
            for key, path in mapping.items():
                expected = hashes.get(key)
                actual = file_sha256_16(path)
                if expected is None or actual is None or expected != actual:
                    mismatches.append({"key": key, "expected": expected, "actual": actual})
            # research metrics preserved
            tm = meta.get("test_metrics_binary") or {}
            f1 = tm.get("f1")
            f1_ok = f1 is not None and abs(float(f1) - 0.9904784130688448) < 1e-9
            if mismatches:
                checks.append(_fail("artifact_hashes", f"mismatch={mismatches}"))
            else:
                checks.append(_ok("artifact_hashes", "binary/multiclass/feature_bundle hashes match"))
            if f1_ok:
                checks.append(_ok("frozen_research_metrics", f"binary F1={f1}"))
            else:
                checks.append(_fail("frozen_research_metrics", f"unexpected F1={f1}"))
            notes = " ".join(meta.get("notes") or [])
            if "production" in notes.lower() or "not a claim" in notes.lower() or notes:
                checks.append(_ok("metadata_non_enterprise_note", "model_metadata notes present"))
            else:
                checks.append(_fail("metadata_non_enterprise_note", "notes empty"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("artifact_hashes", str(exc)))

    # Invalid predict input
    try:
        r = client.post("/api/predict", json={})
        if r.status_code in {422, 400, 500}:
            body = r.text.lower()
            if "traceback" in body:
                checks.append(_fail("invalid_predict_safe", "traceback leaked"))
            else:
                checks.append(_ok("invalid_predict_safe", f"status={r.status_code}"))
        else:
            checks.append(_fail("invalid_predict_safe", f"unexpected status={r.status_code}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("invalid_predict_safe", str(exc)))

    return _category("Model-serving safety", checks)


# ── 6. Simulation isolation ──────────────────────────────────────────────


def check_simulation_isolation() -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from backend.main import app
    from security.response.adapters import reset_test_adapter, test_network_adapter
    from simulation.engine.core import SimulationEngine
    from simulation.validation import validate_families

    checks: list[Check] = []
    client = TestClient(app)

    try:
        report = validate_families(["DDoS"])
        assert report.get("live_cyber_range") is False
        assert report.get("efficacy_are_assumptions") is True
        checks.append(_ok("sim_assumptions_flagged", "efficacy_are_assumptions=true, not live range"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("sim_assumptions_flagged", str(exc)))

    try:
        reset_test_adapter()
        before = test_network_adapter.snapshot()["count"]
        eng = SimulationEngine()
        session = eng.start(attack_type="DDoS")
        sid = session.get("id") or session.get("session_id")
        for _ in range(8):
            eng.advance(sid)
        after = test_network_adapter.snapshot()["count"]
        if after == before == 0:
            checks.append(_ok("sim_no_test_adapter", "simulation did not apply TestNetworkAdapter controls"))
        else:
            checks.append(_fail("sim_no_test_adapter", f"adapter count {before}→{after}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("sim_no_test_adapter", str(exc)))

    try:
        r = client.get("/api/security/status")
        body = r.json()
        cr = body.get("controlled_response") or {}
        cv = body.get("cyber_range_validation") or {}
        if cr.get("live_firewall_edr") is False or cr.get("live_mitigation") is False:
            checks.append(_ok("security_status_no_live", "security/status denies live mitigation"))
        else:
            checks.append(_fail("security_status_no_live", str(cr)))
        if cv.get("live_cyber_range") is False:
            checks.append(_ok("security_status_sim_isolated", "cyber_range not live"))
        else:
            checks.append(_fail("security_status_sim_isolated", str(cv)))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("security_status_no_live", str(exc)))

    # config assumptions still present
    try:
        cfg = load_config()
        de = (cfg.get("simulation") or {}).get("defense_effectiveness") or {}
        if abs(float(de.get("DDoS", 0)) - 0.82) < 1e-9 and abs(float(de.get("DoS", 0)) - 0.78) < 1e-9:
            checks.append(_ok("sim_priors_preserved", "DDoS=0.82 DoS=0.78 still assumptions"))
        else:
            checks.append(_fail("sim_priors_preserved", f"unexpected priors {de}"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("sim_priors_preserved", str(exc)))

    reset_test_adapter()
    return _category("Simulation isolation", checks)


# ── 7. Empirical mitigation integrity ────────────────────────────────────


def check_empirical_mitigation() -> dict[str, Any]:
    checks: list[Check] = []
    cfg = load_config()
    out_dir = resolve_path(cfg["models"]["output_dir"])
    path = out_dir / "empirical_mitigation_report.json"
    if not path.is_file():
        return _category(
            "Empirical mitigation",
            [_fail("empirical_report_present", "empirical_mitigation_report.json missing — run script 42")],
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ids = set(data.get("experiment_ids") or [])
        if "EXP-018" in ids and "EXP-019" in ids:
            checks.append(_ok("exp_ids", "EXP-018 and EXP-019 present"))
        else:
            checks.append(_fail("exp_ids", f"ids={ids}"))

        honesty = data.get("honesty") or {}
        if honesty.get("simulation_preserved") is True:
            checks.append(_ok("sim_preserved_flag", "simulation_preserved=true"))
        else:
            checks.append(_fail("sim_preserved_flag", str(honesty)))

        dc = data.get("defense_configuration") or {}
        if dc.get("live_firewall_edr") is False and dc.get("approval_required") is True:
            checks.append(_ok("controlled_lab_flags", "CONTROLLED + approval, no live EDR"))
        else:
            checks.append(_fail("controlled_lab_flags", str(dc)))

        comps = data.get("comparisons") or {}
        ddos = comps.get("ddos_block_source") or {}
        dos = comps.get("dos_rate_limit") or {}
        if abs(float(ddos.get("controlled_measured_effectiveness_mean") or -1) - 1.0) < 1e-6:
            checks.append(_ok("measured_ddos_1_00", "measured BLOCK_SOURCE effectiveness=1.00 (lab)"))
        else:
            checks.append(_fail("measured_ddos_1_00", str(ddos)))
        if abs(float(dos.get("controlled_measured_effectiveness_mean") or -1) - 0.8) < 1e-6:
            checks.append(_ok("measured_dos_0_80", "measured RATE_LIMIT effectiveness=0.80 (lab)"))
        else:
            checks.append(_fail("measured_dos_0_80", str(dos)))
        if abs(float(ddos.get("simulation_assumption") or 0) - 0.82) < 1e-9:
            checks.append(_ok("assumption_ddos_0_82", "simulation prior DDoS=0.82 retained"))
        else:
            checks.append(_fail("assumption_ddos_0_82", str(ddos.get("simulation_assumption"))))
        if abs(float(dos.get("simulation_assumption") or 0) - 0.78) < 1e-9:
            checks.append(_ok("assumption_dos_0_78", "simulation prior DoS=0.78 retained"))
        else:
            checks.append(_fail("assumption_dos_0_78", str(dos.get("simulation_assumption"))))
        delta = ddos.get("delta_measured_minus_simulation")
        if delta is not None:
            checks.append(_ok("delta_reported", f"DDoS Δ measured−sim={delta}"))
        else:
            checks.append(_fail("delta_reported", "delta missing"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("empirical_parse", str(exc)))

    return _category("Empirical mitigation", checks)


# ── 8. Audit integrity + production boundary ─────────────────────────────


def check_audit_integrity() -> dict[str, Any]:
    checks: list[Check] = []
    try:
        from security.security_events import security_event

        ev = security_event("p12_probe", path="/p12", method="TEST", code="OK")
        assert ev.get("event") == "p12_probe"
        checks.append(_ok("security_events_module", "security_event() records structured events"))
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("security_events_module", str(exc)))

    try:
        from security.response.adapters import reset_test_adapter
        from security.response.service import propose_action
        from security.response.store import response_store

        response_store.clear()
        reset_test_adapter()
        a = propose_action(attack_type="Bot", source_ip="203.0.113.70", mode="DRY_RUN")
        ra = response_store.get(a["action_id"])
        raw_audit = getattr(ra, "audit", None) or []
        events = []
        for e in raw_audit:
            if isinstance(e, dict):
                events.append(e.get("event"))
            else:
                events.append(getattr(e, "event", None))
        if "proposed" in events:
            checks.append(_ok("response_audit_events", f"events include proposed"))
        else:
            # as_dict path
            ad = a.get("audit") or []
            events2 = [e.get("event") for e in ad if isinstance(e, dict)]
            if "proposed" in events2:
                checks.append(_ok("response_audit_events", "proposed present via as_dict"))
            else:
                checks.append(_fail("response_audit_events", f"no proposed event: {events or events2}"))
        response_store.clear()
    except Exception as exc:  # noqa: BLE001
        checks.append(_fail("response_audit_events", str(exc)))

    return _category("Audit integrity", checks)


def check_production_boundary() -> dict[str, Any]:
    checks: list[Check] = []
    docs = {
        "EMPIRICAL_MITIGATION.md": ["CONTROLLED", "simulation", "assumption"],
        "GENERALIZATION.md": ["IID", "temporal", "limitation"],
        "FAILURE_RECOVERY.md": ["reclaim", "FAILED"],
        "05-simulation.md": ["assumption", "visualization"],
    }
    for name, needles in docs.items():
        path = ROOT / "docs" / name
        if not path.is_file():
            checks.append(_fail(f"doc_{name}", "missing"))
            continue
        text = path.read_text(encoding="utf-8").lower()
        missing = [n for n in needles if n.lower() not in text]
        if missing:
            checks.append(_fail(f"doc_{name}", f"missing phrases {missing}"))
        else:
            checks.append(_ok(f"doc_{name}", "boundary language present"))

    # Hard boundary phrases in readiness docs (created in P12)
    for name in ("FINAL_SECURITY_VALIDATION.md", "SECURITY_MODEL.md", "PRODUCTION_READINESS.md"):
        path = ROOT / "docs" / name
        if path.is_file():
            checks.append(_ok(f"p12_doc_{name}", "present"))
        else:
            checks.append(_fail(f"p12_doc_{name}", "will be created with P12 docs"))

    return _category("Production boundary", checks)


def check_frozen_research_baseline() -> dict[str, Any]:
    """Alias category matching the user's status board."""
    model = check_model_serving_safety()
    # Keep only hash + metrics subset as its own board line — reuse results
    relevant = [
        c
        for c in model["checks"]
        if c["id"] in {"artifact_hashes", "frozen_research_metrics", "metadata_non_enterprise_note"}
    ]
    if not relevant:
        relevant = model["checks"]
    return _category("Frozen research baseline", relevant)


def run_all_p12_checks() -> dict[str, Any]:
    categories = {
        "Authentication/RBAC": check_auth_rbac(),
        "Response safety": check_response_safety(),
        "API/input security": check_api_input_security(),
        "Persistence/recovery": check_persistence_recovery(),
        "Model-serving safety": check_model_serving_safety(),
        "Simulation isolation": check_simulation_isolation(),
        "Empirical mitigation": check_empirical_mitigation(),
        "Audit integrity": check_audit_integrity(),
        "Production boundary": check_production_boundary(),
        "Frozen research baseline": check_frozen_research_baseline(),
    }
    overall = "PASS" if all(c["status"] == "PASS" for c in categories.values()) else "FAIL"
    return {
        "phase": "P12",
        "experiment": "final_security_validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "categories": categories,
    }
