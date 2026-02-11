from __future__ import annotations


def test_tool_registry_telegram_send_message_defaults_to_configured_chat(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")
    monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT", "95576236")

    from app.core.db import SessionLocal, engine
    from app.core.tool_registry import execute_pending_action
    from app.models.base import Base
    from app.models.tables import OutboxMessage, PendingAction, Tenant
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        action = PendingAction(
            id=new_uuid(),
            tenant_id=tenant_id,
            user_id="u1",
            risk_level="YELLOW",
            action_type="telegram.send_message",
            payload={"text": "hello"},
            status="APPROVED",
            confirmation_token_hash=None,
            created_at=now_utc(),
            decided_at=None,
        )
        db.add(action)
        db.commit()

        res = execute_pending_action(db, action=action)
        db.commit()

        assert res.ok is True
        assert res.status == "QUEUED"
        assert res.outbox_id

        m = db.query(OutboxMessage).filter(OutboxMessage.id == res.outbox_id).one()
        assert m.channel == "telegram"
        assert m.to == "95576236"
        assert "hello" in m.body
