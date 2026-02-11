from __future__ import annotations


def test_outbox_idempotency_same_payload_returns_same_id(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")

    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import Tenant
    from app.outbox.service import create_outbox_message
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        db.commit()

        payload = {
            "schema": "clowbot.outbox.v1",
            "kind": "telegram",
            "idempotency_key": "",
            "context": {"source": "test"},
            "policy": {"risk": "YELLOW", "requires_approval": False, "allowlist": {"telegram_chats": ["95576236"]}},
            "message": {"chat": {"chat_id": "95576236", "username": None}, "text": "hi"},
            "attachments": [],
        }

        id1 = create_outbox_message(db=db, tenant_id=tenant_id, user_id="u1", payload_dict=payload)
        id2 = create_outbox_message(db=db, tenant_id=tenant_id, user_id="u1", payload_dict=payload)
        assert id1 == id2
