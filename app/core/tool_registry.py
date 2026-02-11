from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.tables import AuditLog, OutboxMessage, PendingAction
from app.util.ids import new_uuid
from app.util.time import now_utc


class ConfirmationRequired(Exception):
    pass


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    status: str
    detail: str | None = None
    outbox_id: str | None = None


def _audit(
    db: Session,
    *,
    tenant_id: str | None,
    user_id: str | None,
    event_type: str,
    severity: str,
    message: str,
    context: dict,
) -> None:
    db.add(
        AuditLog(
            id=new_uuid(),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            message=message,
            context=context or {},
            created_at=now_utc(),
        )
    )


def execute_pending_action(db: Session, *, action: PendingAction) -> ToolResult:
    """Execute a pending action through ToolRegistry.

    This is a STUB executor: it never sends outside. Instead:
    - GREEN: returns ok
    - YELLOW: writes to Outbox (queued)
    - RED: requires action.status == APPROVED, otherwise raises ConfirmationRequired
    """

    _audit(
        db,
        tenant_id=action.tenant_id,
        user_id=action.user_id,
        event_type="TOOL_CALL",
        severity="INFO",
        message=f"tool={action.action_type} risk={action.risk_level}",
        context={"action_id": action.id, "payload": action.payload},
    )

    if action.risk_level == "RED" and action.status != "APPROVED":
        _audit(
            db,
            tenant_id=action.tenant_id,
            user_id=action.user_id,
            event_type="CONFIRMATION_REQUIRED",
            severity="WARN",
            message="RED action blocked: not approved",
            context={"action_id": action.id, "tool": action.action_type},
        )
        raise ConfirmationRequired("RED action requires approval")

    # GREEN noop
    if action.action_type in {"noop", "internal.noop"}:
        _audit(
            db,
            tenant_id=action.tenant_id,
            user_id=action.user_id,
            event_type="TOOL_RESULT",
            severity="INFO",
            message="noop",
            context={"action_id": action.id, "ok": True},
        )
        return ToolResult(ok=True, status="DONE")

    # Convenience action: telegram.send_message
    if action.action_type in {"telegram.send_message", "telegram.send"}:
        from app.core.config import settings

        channel = "telegram"
        to = (action.payload or {}).get("to") or settings.TELEGRAM_DEFAULT_CHAT
        subject = None
        body = (action.payload or {}).get("text") or (action.payload or {}).get("body") or (action.payload or {}).get("message")
        if not body:
            body = str(action.payload)
    else:
        # For now anything that would be an external side-effect is routed to Outbox.
        # Expected payload keys (soft): channel/to/subject/body
        channel = (action.payload or {}).get("channel") or "stub"
        to = (action.payload or {}).get("to") or "(unspecified)"
        subject = (action.payload or {}).get("subject")
        body = (action.payload or {}).get("body") or (action.payload or {}).get("message") or str(action.payload)

    outbox = OutboxMessage(
        id=new_uuid(),
        tenant_id=action.tenant_id,
        user_id=action.user_id,
        channel=channel,
        to=to,
        subject=subject,
        body=body,
        meta={"source_pending_action_id": action.id, "tool": action.action_type, "risk": action.risk_level},
        status="QUEUED",
        created_at=now_utc(),
        sent_at=None,
    )
    db.add(outbox)

    _audit(
        db,
        tenant_id=action.tenant_id,
        user_id=action.user_id,
        event_type="TOOL_RESULT",
        severity="INFO",
        message="queued_to_outbox",
        context={"action_id": action.id, "outbox_id": outbox.id, "ok": True},
    )

    return ToolResult(ok=True, status="QUEUED", outbox_id=outbox.id)
