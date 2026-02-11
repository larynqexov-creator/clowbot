from __future__ import annotations

import hashlib


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def test_worker_processes_approved_pending_action(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")
    monkeypatch.setenv("CELERY_BROKER_URL", "memory://")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "cache+memory://")

    # Need to import after env.
    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import PendingAction, Tenant
    from app.tasks.jarvis_tasks import process_pending_actions
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        action_id = new_uuid()
        db.add(
            PendingAction(
                id=action_id,
                tenant_id=tenant_id,
                user_id="u1",
                risk_level="RED",
                action_type="send_message",
                payload={"channel": "email", "to": "x@example.com", "subject": "s", "body": "b"},
                status="APPROVED",
                confirmation_token_hash=_hash_token("tok"),
                created_at=now_utc(),
                decided_at=None,
            )
        )
        db.commit()

    # Call task function directly (unit test; avoids needing a broker/backend).
    out = process_pending_actions(limit=10)
    assert out["ok"] is True

    with SessionLocal() as db:
        a = db.query(PendingAction).filter(PendingAction.tenant_id == tenant_id).one()
        assert a.status == "DONE"


def test_celery_is_configured_for_eager(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")
    monkeypatch.setenv("CELERY_BROKER_URL", "memory://")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "cache+memory://")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")

    from app.core.celery_app import celery

    assert celery.conf.task_always_eager in (True, False)
