"""P2 response service: propose → dry-run → approve/reject → dry execute → audit."""
from __future__ import annotations

from typing import Any

from security.response.dry_run import DryRunExecutor, LiveAdapterForbiddenError, LiveNetworkAdapter
from security.response.planner import build_proposal_fields
from security.response.store import new_action_id, response_store
from security.response.types import (
    ALLOWED_ACTION_TYPES,
    ActionStatus,
    ExecutionMode,
    ResponseAction,
    utc_now_iso,
)

dry_run_executor = DryRunExecutor()
_live_adapter = LiveNetworkAdapter()  # never wired for apply in P2


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
    # Reject obvious injection / path tricks for future adapter safety
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
    actor: str | None = "analyst",
    source: str = "api",
) -> dict[str, Any]:
    """Create a PROPOSED action and immediately attach a dry-run preview (default)."""
    if mode != ExecutionMode.DRY_RUN.value:
        raise ResponseError(
            "LIVE_MODE_DISABLED",
            "Only DRY_RUN mode is allowed in P2; live adapters are not enabled.",
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
    if action_type:
        fields["action_type"] = _validate_action_type(action_type)
    else:
        fields["action_type"] = _validate_action_type(fields["action_type"])

    tgt = _validate_target(target or fields["target"])
    duration = int(duration_minutes if duration_minutes is not None else fields["duration_minutes"])
    if duration < 0 or duration > 24 * 60:
        raise ResponseError("INVALID_DURATION", "duration_minutes must be 0–1440", http_status=422)

    action = ResponseAction(
        action_id=new_action_id(),
        action_type=fields["action_type"],
        incident_id=incident_id,
        source=source,
        target=tgt,
        reason=str(fields["reason"]),
        risk_score=float(risk_score) if risk_score is not None else None,
        severity=str(fields["severity"]),
        duration_minutes=duration,
        mode=ExecutionMode.DRY_RUN.value,
        status=ActionStatus.PROPOSED.value,
        created_by=actor,
        attack_type=attack_type,
    )
    preview = dry_run_executor.preview(action)
    action.dry_run_preview = preview
    response_store.create(action)
    response_store.append_audit(
        action,
        event="proposed",
        actor=actor,
        detail={
            "action_type": action.action_type,
            "target": action.target,
            "mode": action.mode,
            "incident_id": incident_id,
            "dry_run_preview": preview,
        },
    )
    response_store.append_audit(
        action,
        event="dry_run_preview",
        actor="system",
        detail={"message": preview, "live_network_change": False},
    )
    return action.as_dict()


def run_dry_run(action_id: str, *, actor: str | None = "analyst") -> dict[str, Any]:
    action = response_store.get(action_id)
    if action is None:
        raise ResponseError("NOT_FOUND", f"Unknown action {action_id}", http_status=404)
    if action.status == ActionStatus.REJECTED.value:
        raise ResponseError("REJECTED", "Cannot dry-run a rejected action", http_status=409)

    result = dry_run_executor.execute(action)
    action.dry_run_preview = result["message"]
    response_store.append_audit(
        action,
        event="dry_run",
        actor=actor,
        detail=result,
    )
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
        detail={"mode": action.mode, "live_network_change": False},
    )

    # P2: approval auto-runs dry-run execution only (never live adapter)
    exec_result = _execute_dry_only(action, actor=actor)
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
    """Explicit execute — only from APPROVED; still dry-run only in P2."""
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
    result = _execute_dry_only(action, actor=actor)
    return {"ok": True, "action": action.as_dict(), "execution": result}


def _execute_dry_only(action: ResponseAction, *, actor: str | None) -> dict[str, Any]:
    if action.mode != ExecutionMode.DRY_RUN.value:
        # Defense in depth — never call live adapter
        try:
            _live_adapter.apply(action)
        except LiveAdapterForbiddenError as exc:
            action.status = ActionStatus.FAILED.value
            action.result = str(exc)
            response_store.append_audit(
                action,
                event="execution_blocked",
                actor=actor,
                detail={"error": str(exc)},
            )
            raise ResponseError("LIVE_MODE_DISABLED", str(exc), http_status=422) from exc

    action.status = ActionStatus.EXECUTING.value
    response_store.append_audit(action, event="executing", actor=actor, detail={"mode": "DRY_RUN"})
    try:
        result = dry_run_executor.execute(action)
        action.status = ActionStatus.SUCCEEDED.value
        action.executed_at = utc_now_iso()
        action.result = result["message"]
        response_store.append_audit(action, event="succeeded", actor=actor, detail=result)

        verify = dry_run_executor.verify(action)
        action.status = ActionStatus.VERIFIED.value
        action.verified_at = utc_now_iso()
        response_store.append_audit(action, event="verified", actor="system", detail=verify)
        return {"dry_run": result, "verification": verify, "live_network_change": False}
    except Exception as exc:  # noqa: BLE001
        action.status = ActionStatus.FAILED.value
        action.result = str(exc)
        action.executed_at = utc_now_iso()
        response_store.append_audit(
            action,
            event="failed",
            actor=actor,
            detail={"error": str(exc)},
        )
        raise ResponseError("EXECUTION_FAILED", str(exc), http_status=500) from exc


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


def propose_from_incident(incident: dict[str, Any], *, actor: str | None = "analyst") -> dict[str, Any]:
    """Convenience: build proposal from an incident record dict."""
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
    )


def response_capabilities() -> dict[str, Any]:
    return {
        "phase": "P2",
        "mode_default": ExecutionMode.DRY_RUN.value,
        "live_mitigation": False,
        "action_types": sorted(ALLOWED_ACTION_TYPES),
        "lifecycle": [s.value for s in ActionStatus],
        "endpoints": {
            "propose": "/api/response/actions/propose",
            "dry_run": "/api/response/actions/{id}/dry-run",
            "approve": "/api/response/actions/{id}/approve",
            "reject": "/api/response/actions/{id}/reject",
            "list": "/api/response/actions",
        },
        "notes": [
            "Dry-run is the only execution path in P2.",
            "Approve never invokes firewall/EDR adapters.",
            "Reject guarantees no execution.",
        ],
    }
