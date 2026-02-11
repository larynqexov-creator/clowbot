from __future__ import annotations

import logging

from app.core.celery_app import celery
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.tool_registry import ConfirmationRequired, execute_pending_action
from app.integrations.telegram import TelegramSendError, send_message
from app.memory.object_store import put_text
from app.models.tables import Document, OutboxMessage, PendingAction
from app.outbox.preview import render_preview_pack
from app.schemas.outbox_v1 import OutboxPayloadV1
from app.util.ids import new_uuid
from app.util.time import now_utc

log = logging.getLogger("jarvis_tasks")


@celery.task(name="app.tasks.jarvis_tasks.process_pending_actions")
def process_pending_actions(*, limit: int = 25) -> dict:
    """Process APPROVED pending actions.

    STUB executor:
    - Executes via ToolRegistry
    - Updates action status: DONE / FAILED
    - External sends are not performed; routed to Outbox.
    """

    db = SessionLocal()
    try:
        actions = (
            db.query(PendingAction)
            .filter(PendingAction.status == "APPROVED")
            .order_by(PendingAction.created_at.asc())
            .limit(limit)
            .all()
        )

        done = 0
        failed = 0
        queued = 0

        for a in actions:
            try:
                res = execute_pending_action(db, action=a)
                if res.status == "QUEUED":
                    a.status = "DONE"  # action completed by producing an outbox item
                    queued += 1
                else:
                    a.status = "DONE"
                a.decided_at = a.decided_at or now_utc()
                db.commit()
                done += 1
            except ConfirmationRequired:
                # Should not happen for APPROVED; keep as APPROVED for visibility
                db.rollback()
                log.warning("Action %s blocked: confirmation required", a.id)
                failed += 1
            except Exception as e:
                db.rollback()
                log.exception("Action %s failed: %s", a.id, str(e))
                # Mark failed
                try:
                    a2 = db.query(PendingAction).filter(PendingAction.id == a.id).one_or_none()
                    if a2:
                        a2.status = "FAILED"
                        a2.decided_at = now_utc()
                        db.commit()
                except Exception:
                    db.rollback()
                failed += 1

        return {"ok": True, "done": done, "queued": queued, "failed": failed}
    finally:
        db.close()


def _audit(db, *, tenant_id: str, user_id: str | None, event_type: str, severity: str, message: str, context: dict) -> None:
    from app.models.tables import AuditLog

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


@celery.task(name="app.tasks.jarvis_tasks.dispatch_outbox")
def dispatch_outbox(*, limit: int = 25) -> dict:
    """Dispatch outbox messages in STUB mode.

    Behavior:
    - QUEUED -> SENDING -> STUB_SENT (or FAILED)
    - Create a preview artifact (Document doc_type=outbox_preview)
    - Write audit events: OUTBOX_DISPATCH_ATTEMPT + OUTBOX_STUB_SENT/OUTBOX_FAILED

    NOTE: This does NOT actually send anything.
    """

    db = SessionLocal()
    try:
        items = (
            db.query(OutboxMessage)
            .filter(OutboxMessage.status == "QUEUED")
            .order_by(OutboxMessage.created_at.asc())
            .limit(limit)
            .all()
        )

        sent = 0
        stub_sent = 0
        failed = 0

        for m in items:
            try:
                _audit(
                    db,
                    tenant_id=m.tenant_id,
                    user_id=m.user_id,
                    event_type="OUTBOX_DISPATCH_ATTEMPT",
                    severity="INFO",
                    message="dispatch_attempt",
                    context={"outbox_id": m.id, "channel": m.channel, "to": m.to},
                )

                # Validate/normalize payload (fallback for legacy rows).
                payload_dict = m.payload

                if not payload_dict:
                    # Legacy rows: if channel is unknown, keep stub behavior.
                    if m.channel not in {"email", "telegram", "github_issue"}:
                        preview_doc = Document(
                            id=new_uuid(),
                            tenant_id=m.tenant_id,
                            workflow_id=None,
                            domain="outbox",
                            doc_type="outbox_preview",
                            title=f"Outbox preview: {m.channel} -> {m.to}",
                            content_text=f"# Outbox Preview — {m.channel}\n\n{m.body}\n",
                            object_key=None,
                            meta={"outbox_id": m.id},
                            created_at=now_utc(),
                        )
                        db.add(preview_doc)
                        m.meta = dict(m.meta or {})
                        m.meta["preview"] = {"document_id": preview_doc.id, "object_keys": {}}
                        m.status = "STUB_SENT"
                        m.sent_at = now_utc()
                        db.commit()
                        stub_sent += 1
                        continue

                    payload_dict = {
                        "schema": "clowbot.outbox.v1",
                        "kind": m.channel,
                        "idempotency_key": m.idempotency_key or "",
                        "context": {"source": "legacy"},
                        "policy": {"risk": "YELLOW", "requires_approval": False, "allowlist": {}},
                        "message": {
                            "chat": {"chat_id": m.to, "username": None},
                            "parse_mode": "Markdown",
                            "text": m.body,
                            "disable_web_page_preview": True,
                            "reply_to_message_id": None,
                            "silent": False,
                        }
                        if m.channel == "telegram"
                        else {
                            "from": {"name": "ClowBot", "email": "noreply@local"},
                            "to": [{"email": m.to, "name": None}],
                            "cc": [],
                            "bcc": [],
                            "reply_to": [],
                            "subject": m.subject or "(no subject)",
                            "body": {"text": m.body},
                            "headers": {},
                        },
                        "attachments": [],
                    }

                from pydantic import TypeAdapter

                payload: OutboxPayloadV1 = TypeAdapter(OutboxPayloadV1).validate_python(payload_dict)

                # Approval gate: if requires approval, only dispatch after outbox meta has approved flag.
                approved = bool((m.meta or {}).get("approved"))
                if payload.policy.requires_approval and not approved:
                    # Keep queued; do not fail.
                    _audit(
                        db,
                        tenant_id=m.tenant_id,
                        user_id=m.user_id,
                        event_type="OUTBOX_BLOCKED",
                        severity="INFO",
                        message="requires_approval",
                        context={"outbox_id": m.id},
                    )
                    continue

                # Mark sending (best-effort idempotency; proper row-locking on Postgres can be added later).
                m.status = "SENDING"
                db.commit()

                pack = render_preview_pack(outbox_id=m.id, payload=payload, status=m.status)

                # Store raw artifacts (best-effort) to MinIO.
                base = f"{m.tenant_id}/outbox/{m.id}"
                raw_key = put_text(object_key=f"{base}/{pack.channel_raw_name}", text=pack.channel_raw, content_type="text/plain")
                payload_key = put_text(object_key=f"{base}/preview_payload.json", text=pack.preview_payload_json, content_type="application/json")

                preview_doc = Document(
                    id=new_uuid(),
                    tenant_id=m.tenant_id,
                    workflow_id=None,
                    domain="outbox",
                    doc_type="outbox_preview",
                    title=f"Outbox preview: {payload.kind} -> {m.to}",
                    content_text=pack.preview_md,
                    object_key=None,
                    meta={"outbox_id": m.id},
                    created_at=now_utc(),
                )
                db.add(preview_doc)

                m.meta = dict(m.meta or {})
                m.meta.setdefault("preview", {})
                m.meta["preview"]["document_id"] = preview_doc.id
                m.meta["preview"].setdefault("object_keys", {})
                m.meta["preview"]["object_keys"]["preview_payload_json"] = payload_key
                m.meta["preview"]["object_keys"][pack.channel_raw_name] = raw_key

                # Telegram send (real) optional.
                if payload.kind == "telegram" and settings.TELEGRAM_BOT_TOKEN:
                    chat_id = payload.message.chat.chat_id or payload.message.chat.username
                    allow = {x.strip() for x in (settings.TELEGRAM_ALLOWLIST_CHATS or "").split(",") if x.strip()}
                    if not chat_id or chat_id not in allow:
                        raise TelegramSendError(f"Telegram chat not allowlisted: {chat_id}")

                    resp = send_message(
                        token=settings.TELEGRAM_BOT_TOKEN,
                        chat_id=chat_id,
                        text=payload.message.text,
                        parse_mode=None if payload.message.parse_mode == "Plain" else payload.message.parse_mode,
                        disable_preview=payload.message.disable_web_page_preview,
                    )

                    m.status = "SENT"
                    m.sent_at = now_utc()
                    m.meta["telegram_result"] = {"message_id": resp.get("result", {}).get("message_id")}

                    _audit(
                        db,
                        tenant_id=m.tenant_id,
                        user_id=m.user_id,
                        event_type="OUTBOX_SENT",
                        severity="INFO",
                        message="telegram_sent",
                        context={"outbox_id": m.id, "preview_document_id": preview_doc.id},
                    )
                    db.commit()
                    sent += 1
                else:
                    m.status = "STUB_SENT"
                    m.sent_at = now_utc()

                    _audit(
                        db,
                        tenant_id=m.tenant_id,
                        user_id=m.user_id,
                        event_type="OUTBOX_STUB_SENT",
                        severity="INFO",
                        message="stub_sent",
                        context={"outbox_id": m.id, "preview_document_id": preview_doc.id},
                    )
                    db.commit()
                    stub_sent += 1
            except Exception as e:
                db.rollback()
                try:
                    m2 = db.query(OutboxMessage).filter(OutboxMessage.id == m.id).one_or_none()
                    if m2:
                        m2.status = "FAILED"
                        _audit(
                            db,
                            tenant_id=m2.tenant_id,
                            user_id=m2.user_id,
                            event_type="OUTBOX_FAILED",
                            severity="ERROR",
                            message=str(e),
                            context={"outbox_id": m2.id},
                        )
                        db.commit()
                except Exception:
                    db.rollback()
                failed += 1

        return {"ok": True, "sent": sent, "stub_sent": stub_sent, "failed": failed}
    finally:
        db.close()
