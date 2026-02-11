from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
from app.core.db import SessionLocal
from app.models.tables import OutboxMessage

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def list_outbox(ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, _ = ctx

    items = (
        db.query(OutboxMessage)
        .filter(OutboxMessage.tenant_id == tenant_id)
        .order_by(OutboxMessage.created_at.desc())
        .limit(200)
        .all()
    )

    return {
        "items": [
            {
                "id": m.id,
                "channel": m.channel,
                "to": m.to,
                "subject": m.subject,
                "body": m.body,
                "status": m.status,
                "created_at": m.created_at,
                "sent_at": m.sent_at,
                "idempotency_key": m.idempotency_key,
                "payload": m.payload,
                "meta": m.meta,
            }
            for m in items
        ]
    }
