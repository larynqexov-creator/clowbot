from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
from app.core.db import SessionLocal
from app.models.tables import PendingAction
from app.outbox.service import create_outbox_message
from app.util.ids import new_uuid
from app.util.time import now_utc

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/telegram/send")
def telegram_send(payload: dict, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, user_id = ctx

    text = (payload or {}).get("text")
    to = (payload or {}).get("to")
    allow = (payload or {}).get("allowlist") or {"telegram_chats": [to] if to else []}

    outbox_payload = {
        "schema": "clowbot.outbox.v1",
        "kind": "telegram",
        "idempotency_key": "",
        "context": {"source": "api.tools"},
        "policy": {
            "risk": "YELLOW",
            "requires_approval": False,
            "allowlist": {
                "email_domains": [],
                "emails": [],
                "telegram_chats": allow.get("telegram_chats") or ([] if not to else [to]),
                "github_repos": [],
            },
        },
        "message": {
            "chat": {"chat_id": to, "username": None},
            "parse_mode": "Markdown",
            "text": text,
            "disable_web_page_preview": True,
            "reply_to_message_id": None,
            "silent": False,
        },
        "attachments": [],
    }

    outbox_id = create_outbox_message(db=db, tenant_id=tenant_id, user_id=user_id, payload_dict=outbox_payload)

    # If requires approval, create pending action.
    # Note: enforcement happens in create_outbox_message and sets requires_approval if allowlist mismatch.
    # We re-load row.
    from app.models.tables import OutboxMessage

    m = db.query(OutboxMessage).filter(OutboxMessage.id == outbox_id).one()
    pa_id = None
    if (m.payload or {}).get("policy", {}).get("requires_approval"):
        pa = PendingAction(
            id=new_uuid(),
            tenant_id=tenant_id,
            user_id=user_id,
            risk_level="RED",
            action_type="outbox.send",
            payload={"outbox_id": outbox_id},
            status="PENDING",
            confirmation_token_hash=None,
            created_at=now_utc(),
            decided_at=None,
        )
        db.add(pa)
        db.commit()
        pa_id = pa.id

    return {"outbox_id": outbox_id, "pending_action_id": pa_id}
