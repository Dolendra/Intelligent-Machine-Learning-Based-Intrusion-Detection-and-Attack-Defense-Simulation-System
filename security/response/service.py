"""Response service: propose → dry-run → approve → adapter execute → verify → rollback/expire."""
from __future__ import annotations

from typing import Any

from security.response.adapters import get_adapter, list_adapters, reset_test_adapter
from security.response.adapters.base import AdapterError
from security.response.adapters.live_forbidden import LiveAdapterForbiddenError
from security.response.adapters.reversibility import inverse_action, is_reversible
from security.response.planner import build_proposal_fields
from security.response.store import new_action_id, response_store
from security.response.types import (
    ALLOWED_ACTION_TYPES,
    ALLOWED_MODES,
    ActionStatus,
    ExecutionMode,
    ResponseAction,
    parse_iso,
    utc_now,
    utc_now_iso,
)


class ResponseError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def _validate_target(target: str | None) -> str:
    t = (target or "").strip()
    if not t or len(t) > 256:
        raise ResponseError("INVALID_TARGET", "target is required (1–256 chars)", http_status=422)
    if any(x in t for x in ("\n", "\r", ";", "|", "`", "$(")):
        raise ResponseError("INVALID_TARGET", "target contains forbidden characters", http_status=422)
    return t


def _validate_action_type(action_type: str) -> str:
    at = (action_type or "").strip().upper()
    if at not in ALLOWED_ACTION_TYPES:
        raise ResponseError(
            "INVALID_ACTION",
            f"Unsupported action_type '{action_type}'. Allowed: {sorted(ALLOWED_ACTION_TYPES)}",
            http_status=422,
        )
    return at


def _validate_mode(mode: str) -> str:
    m = (mode or ExecutionMode.DRY_RUN.value).strip().upper()
    if m == ExecutionMode.LIVE.value:
        raise ResponseError(
            "LIVE_MODE_DISABLED",
            "LIVE mode is disabled in P3. Use DRY_RUN or CONTROLLED (test_network).",
            http_status=422,
        )
    if m not in ALLOWED_MODES:
        raise ResponseError(
            "INVALID_MODE",
            f"Unsupported mode '{mode}'. Allowed: {sorted(ALLOWED_MODES)}",
            http_status=422,
        )
    return m


def propose_action(
    *,
    attack_type: str,
    incident_id: str | None = None,
    severity: str | None = None,
    risk_score: float | None = None,
    recommendation: dict[str, Any] | None = None,
    source_ip: str | None = None,
    host: str | None = None,
    target: str | None = None,
    action_type: str | None = None,
    reason: str | None = None,
    duration_minutes: int | None = None,
    mode: str = ExecutionMode.DRY_RUN.value,
    adapter: str | None = None,
    actor: str | None = "analyst",
    source: str = "api",
) -> dict[str, Any]:
    mode_v = _validate_mode(mode)
    try:
        adapter_obj = get_adapter(adapter, mode=mode_v)
    except KeyError as exc:
        raise ResponseError("UNKNOWN_ADAPTER", str(exc), http_status=422) from exc
    if adapter_obj.touches_real_network:
        raise ResponseError(
            "LIVE_ADAPTER_FORBIDDEN",
            "Live adapters cannot be selected in P3.",
            http_status=422,
        )

    fields = build_proposal_fields(
        attack_type=attack_type,
        severity=severity,
        risk_score=risk_score,
        recommendation=recommendation,
        source_ip=source_ip,
        host=host,
        reason=reason,
    )
    atype = _validate_action_type(action_type or fields["action_type"])
    tgt = _validate_target(target or fields["target"])
    duration = int(duration_minutes if duration_minutes is not None else fields["duration_minutes"])
    if duration < 0 or duration > 24 * 60:
        raise ResponseError("INVALID_DURATION", "duration_minutes must be 0–1440", http_status=422)

    action = ResponseAction(
        action_id=new_action_id(),
        action_type=atype,
        incident_id=incident_id,
        source=source,
        target=tgt,
        reason=str(fields["reason"]),
        risk_score=float(risk_score) if risk_score is not None else None,
        severity=str(fields["severity"]),
        duration_minutes=duration,
        mode=mode_v,
        adapter=adapter_obj.name,
        status=ActionStatus.PROPOSED.value,
        created_by=actor,
        attack_type=attack_type,
        reversible=is_reversible(atype),
        inverse_action=inverse_action(atype),
        live_network_change=False,
    )
    try:
        adapter_obj.validate(action)
        preview = adapter_obj.preview(action)
    except AdapterError as exc:
        raise ResponseError(exc.code, exc.message, http_status=422) from exc

    action.dry_run_preview = str(preview.get("message") or "")
    response_store.create(action)
    response_store.append_audit(
        action,
        event="proposed",
        actor=actor,
        detail={
            "action_type": action.action_type,
            "target": action.target,
            "mode": action.mode,
            "adapter": action.adapter,
            "incident_id": incident_id,
            "preview": action.dry_run_preview,
        },
    )
    response_store.append_audit(
        action,
        event="preview",
        actor="system",
        detail=preview,
    )
    return action.as_dict()


def run_dry_run(action_id: str, *, actor: str | None = "analyst") -> dict[str, Any]:
    """Always uses DryRunAdapter for a no-side-effect preview (even for CONTROLLED proposals)."""
    action = response_store.get(action_id)
    if action is None:
        raise ResponseError("NOT_FOUND", f"Unknown action {action_id}", http_status=404)
    if action.status == ActionStatus.REJECTED.value:
        raise ResponseError("REJECTED", "Cannot dry-run a rejected action", http_status=409)

    dry = get_adapter("dry_run")
    try:
        result = dry.execute(action)
    except AdapterError as exc:
        raise ResponseError(exc.code, exc.message, http_status=422) from exc
    action.dry_run_preview = result.get("message")
    response_store.append_audit(action, event="dry_run", actor=actor, detail=result)
    return {"ok": True, "action": action.as_dict(), "dry_run": result}


def approve_action(action_id: str, *, actor: str | None = "responder") -> dict[str, Any]:
    action = response_store.get(action_id)
    if action is None:
        raise ResponseError("NOT_FOUND", f"Unknown action {action_id}", http_status=404)
    if action.status == ActionStatus.REJECTED.value:
        raise ResponseError("REJECTED", "Rejected actions cannot be approved", http_status=409)
    if action.status != ActionStatus.PROPOSED.value:
        raise ResponseError(
            "ALREADY_DECIDED",
            f"Action is '{action.status}'; cannot approve twice",
            http_status=409,
        )

    action.status = ActionStatus.APPROVED.value
    action.approved_at = utc_now_iso()
    action.approved_by = actor
    response_store.append_audit(
        action,
        event="approved",
        actor=actor,
        detail={"mode": action.mode, "adapter": action.adapter, "live_network_change": False},
    )
    exec_result = _execute_with_adapter(action, actor=actor)
    return {"ok": True, "action": action.as_dict(), "execution": exec_result}


def reject_action(
    action_id: str,
    *,
    actor: str | None = "responder",
    reason: str | None = None,
) -> dict[str, Any]:
    action = response_store.get(action_id)
    if action is None:
        raise ResponseError("NOT_FOUND", f"Unknown action {action_id}", http_status=404)
    if action.status != ActionStatus.PROPOSED.value:
        raise ResponseError(
            "ALREADY_DECIDED",
            f"Action is '{action.status}'; cannot reject",
            http_status=409,
        )
    action.status = ActionStatus.REJECTED.value
    action.rejected_at = utc_now_iso()
    action.rejected_by = actor
    action.rejection_reason = reason or "Rejected by analyst"
    response_store.append_audit(
        action,
        event="rejected",
        actor=actor,
        detail={"reason": action.rejection_reason, "executed": False},
    )
    return {"ok": True, "action": action.as_dict(), "executed": False}


def execute_action(action_id: str, *, actor: str | None = "responder") -> dict[str, Any]:
    action = response_store.get(action_id)
    if action is None:
        raise ResponseError("NOT_FOUND", f"Unknown action {action_id}", http_status=404)
    if action.status == ActionStatus.PROPOSED.value:
        raise ResponseError("NOT_APPROVED", "Unapproved actions cannot execute", http_status=409)
    if action.status == ActionStatus.REJECTED.value:
        raise ResponseError("REJECTED", "Rejected actions cannot execute", http_status=409)
    if action.status != ActionStatus.APPROVED.value:
        raise ResponseError(
            "ALREADY_EXECUTED",
            f"Action already in status '{action.status}'",
            http_status=409,
        )
    result = _execute_with_adapter(action, actor=actor)
    return {"ok": True, "action": action.as_dict(), "execution": result}


def _execute_with_adapter(action: ResponseAction, *, actor: str | None) -> dict[str, Any]:
    try:
        adapter = get_adapter(action.adapter, mode=action.mode)
    except KeyError as exc:
        raise ResponseError("UNKNOWN_ADAPTER", str(exc), http_status=500) from exc

    if adapter.touches_real_network:
        action.status = ActionStatus.FAILED.value
        action.result = "Live adapter blocked"
        response_store.append_audit(
            action,
            event="execution_blocked",
            actor=actor,
            detail={"error": "LIVE_ADAPTER_FORBIDDEN"},
        )
        raise ResponseError("LIVE_ADAPTER_FORBIDDEN", "Live adapters are disabled in P3", http_status=422)

    action.status = ActionStatus.EXECUTING.value
    response_store.append_audit(
        action,
        event="executing",
        actor=actor,
        detail={"mode": action.mode, "adapter": adapter.name},
    )

    try:
        result = adapter.execute(action)
    except (AdapterError, LiveAdapterForbiddenError) as exc:
        action.status = ActionStatus.FAILED.value
        action.result = getattr(exc, "message", str(exc))
        action.executed_at = utc_now_iso()
        response_store.append_audit(
            action,
            event="failed",
            actor=actor,
            detail={"error": str(exc), "code": getattr(exc, "code", "ADAPTER_ERROR")},
        )
        raise ResponseError(
            getattr(exc, "code", "EXECUTION_FAILED"),
            getattr(exc, "message", str(exc)),
            http_status=500,
        ) from exc
    except Exception as exc:  # noqa: BLE001
        action.status = ActionStatus.FAILED.value
        action.result = str(exc)
        action.executed_at = utc_now_iso()
        response_store.append_audit(action, event="failed", actor=actor, detail={"error": str(exc)})
        raise ResponseError("EXECUTION_FAILED", str(exc), http_status=500) from exc

    action.status = ActionStatus.SUCCEEDED.value
    action.executed_at = utc_now_iso()
    action.result = result.get("message")
    response_store.append_audit(action, event="succeeded", actor=actor, detail=result)

    # Verify — on failure, attempt rollback
    try:
        verify = adapter.verify(action)
    except AdapterError as exc:
        response_store.append_audit(
            action,
            event="verify_failed",
            actor="system",
            detail={"error": exc.message, "code": exc.code},
        )
        rollback_detail = None
        if action.reversible:
            try:
                rollback_detail = adapter.rollback(action)
                action.rollback_status = "ROLLED_BACK"
                action.rolled_back_at = utc_now_iso()
                action.status = ActionStatus.ROLLED_BACK.value
                response_store.append_audit(
                    action,
                    event="rolled_back",
                    actor="system",
                    detail={"reason": "verify_failed", **(rollback_detail or {})},
                )
            except AdapterError as rb_exc:
                action.rollback_status = "ROLLBACK_FAILED"
                action.status = ActionStatus.FAILED.value
                response_store.append_audit(
                    action,
                    event="rollback_failed",
                    actor="system",
                    detail={"error": rb_exc.message},
                )
        else:
            action.status = ActionStatus.FAILED.value
            action.rollback_status = "NOT_REVERSIBLE"
        raise ResponseError("VERIFY_FAILED", exc.message, http_status=500) from exc

    action.verified_at = utc_now_iso()
    response_store.append_audit(action, event="verified", actor="system", detail=verify)

    if action.duration_minutes > 0 and action.reversible:
        action.expires_at = action.compute_expires_at()
        action.status = ActionStatus.ACTIVE.value
        response_store.append_audit(
            action,
            event="activated",
            actor="system",
            detail={"expires_at": action.expires_at},
        )
    else:
        action.status = ActionStatus.VERIFIED.value

    return {
        "adapter": adapter.name,
        "result": result,
        "verification": verify,
        "live_network_change": False,
        "expires_at": action.expires_at,
    }


def rollback_action(action_id: str, *, actor: str | None = "responder") -> dict[str, Any]:
    action = response_store.get(action_id)
    if action is None:
        raise ResponseError("NOT_FOUND", f"Unknown action {action_id}", http_status=404)
    if action.status not in {
        ActionStatus.VERIFIED.value,
        ActionStatus.ACTIVE.value,
        ActionStatus.SUCCEEDED.value,
    }:
        raise ResponseError(
            "INVALID_STATE",
            f"Cannot rollback from status '{action.status}'",
            http_status=409,
        )
    if not action.reversible:
        raise ResponseError(
            "NOT_REVERSIBLE",
            f"{action.action_type} is explicitly non-reversible",
            http_status=422,
        )

    adapter = get_adapter(action.adapter, mode=action.mode)
    if adapter.touches_real_network:
        raise ResponseError("LIVE_ADAPTER_FORBIDDEN", "Live rollback disabled", http_status=422)

    try:
        detail = adapter.rollback(action)
    except AdapterError as exc:
        action.rollback_status = "ROLLBACK_FAILED"
        response_store.append_audit(
            action,
            event="rollback_failed",
            actor=actor,
            detail={"error": exc.message},
        )
        raise ResponseError(exc.code, exc.message, http_status=500) from exc

    action.status = ActionStatus.ROLLED_BACK.value
    action.rollback_status = "ROLLED_BACK"
    action.rolled_back_at = utc_now_iso()
    response_store.append_audit(action, event="rolled_back", actor=actor, detail=detail)
    return {"ok": True, "action": action.as_dict(), "rollback": detail}


def expire_action(action_id: str, *, actor: str | None = "system") -> dict[str, Any]:
    """Expire a time-bound ACTIVE action (cleanup via rollback when reversible)."""
    action = response_store.get(action_id)
    if action is None:
        raise ResponseError("NOT_FOUND", f"Unknown action {action_id}", http_status=404)
    if action.status != ActionStatus.ACTIVE.value:
        raise ResponseError(
            "INVALID_STATE",
            f"Only ACTIVE actions expire (got {action.status})",
            http_status=409,
        )
    expires = parse_iso(action.expires_at)
    if expires and utc_now() < expires:
        raise ResponseError(
            "NOT_YET_EXPIRED",
            f"Action expires at {action.expires_at}",
            http_status=409,
        )

    response_store.append_audit(action, event="expired", actor=actor, detail={"expires_at": action.expires_at})
    if action.reversible:
        try:
            out = rollback_action(action_id, actor=actor)
            action.status = ActionStatus.EXPIRED.value
            response_store.append_audit(
                action,
                event="expired_cleanup",
                actor=actor,
                detail={"via": "rollback"},
            )
            return {"ok": True, "action": action.as_dict(), "cleanup": out.get("rollback")}
        except ResponseError:
            action.status = ActionStatus.EXPIRED.value
            raise
    action.status = ActionStatus.EXPIRED.value
    action.rollback_status = "NOT_REVERSIBLE"
    return {"ok": True, "action": action.as_dict(), "cleanup": None}


def sweep_expired(*, actor: str | None = "system") -> dict[str, Any]:
    """Expire all ACTIVE actions past expires_at."""
    now = utc_now()
    expired_ids: list[str] = []
    errors: list[dict[str, str]] = []
    for action in response_store.list(limit=500):
        if action.status != ActionStatus.ACTIVE.value:
            continue
        expires = parse_iso(action.expires_at)
        if expires is None or now < expires:
            continue
        try:
            expire_action(action.action_id, actor=actor)
            expired_ids.append(action.action_id)
        except ResponseError as exc:
            errors.append({"action_id": action.action_id, "code": exc.code, "message": exc.message})
    return {"ok": True, "expired": expired_ids, "errors": errors}


def get_action(action_id: str) -> dict[str, Any]:
    action = response_store.get(action_id)
    if action is None:
        raise ResponseError("NOT_FOUND", f"Unknown action {action_id}", http_status=404)
    return action.as_dict()


def list_actions(*, incident_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    return [a.as_dict() for a in response_store.list(incident_id=incident_id, limit=limit)]


def action_audit(action_id: str) -> list[dict[str, Any]]:
    action = response_store.get(action_id)
    if action is None:
        raise ResponseError("NOT_FOUND", f"Unknown action {action_id}", http_status=404)
    return list(action.audit)


def propose_from_incident(
    incident: dict[str, Any],
    *,
    actor: str | None = "analyst",
    mode: str = ExecutionMode.DRY_RUN.value,
) -> dict[str, Any]:
    from security.recommendations.engine import recommend

    attack = str(incident.get("attack_type") or "Other")
    sev = incident.get("severity")
    conf = incident.get("confidence")
    rec = recommend(
        attack,
        str(sev) if sev else None,
        confidence=float(conf) if conf is not None else None,
        is_attack=attack != "BENIGN",
    )
    return propose_action(
        attack_type=attack,
        incident_id=str(incident.get("incident_id") or incident.get("incident_code") or ""),
        severity=str(sev) if sev else None,
        risk_score=float(incident["risk_score"]) if incident.get("risk_score") is not None else None,
        recommendation=rec,
        actor=actor,
        source="incident",
        mode=mode,
    )


def response_capabilities() -> dict[str, Any]:
    return {
        "phase": "P3",
        "mode_default": ExecutionMode.DRY_RUN.value,
        "modes_allowed": sorted(ALLOWED_MODES),
        "live_mitigation": False,
        "action_types": sorted(ALLOWED_ACTION_TYPES),
        "lifecycle": [s.value for s in ActionStatus],
        "adapters": list_adapters(),
        "endpoints": {
            "propose": "/api/response/actions/propose",
            "dry_run": "/api/response/actions/{id}/dry-run",
            "approve": "/api/response/actions/{id}/approve",
            "reject": "/api/response/actions/{id}/reject",
            "rollback": "/api/response/actions/{id}/rollback",
            "expire": "/api/response/actions/{id}/expire",
            "adapters": "/api/response/adapters",
            "list": "/api/response/actions",
        },
        "notes": [
            "P3 adds adapter contract + TestNetworkAdapter (simulated control plane).",
            "DRY_RUN and CONTROLLED are allowed; LIVE / firewall / EDR remain forbidden.",
            "Verification failure triggers automatic rollback when the action is reversible.",
            "Time-bound ACTIVE actions can expire and clean up via rollback.",
        ],
    }


__all__ = [
    "ResponseError",
    "propose_action",
    "run_dry_run",
    "approve_action",
    "reject_action",
    "execute_action",
    "rollback_action",
    "expire_action",
    "sweep_expired",
    "get_action",
    "list_actions",
    "action_audit",
    "propose_from_incident",
    "response_capabilities",
    "reset_test_adapter",
]
