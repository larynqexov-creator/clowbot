from __future__ import annotations


def test_outbox_dispatcher_stub_sent_creates_preview(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")

    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import Document, OutboxMessage, Tenant
    from app.tasks.jarvis_tasks import dispatch_outbox
    from app.util.ids import new_uuid
    from app.util.time import now_utc
    from tests.utils_bootstrap import seed_min_bootstrap_docs

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        seed_min_bootstrap_docs(db, tenant_id=tenant_id)
        msg_id = new_uuid()
        db.add(
            OutboxMessage(
                id=msg_id,
                tenant_id=tenant_id,
                user_id="u1",
                channel="email",
                to="x@example.com",
                subject="Hello",
                body="Body",
                meta={},
                status="QUEUED",
                created_at=now_utc(),
                sent_at=None,
            )
        )
        db.commit()

    out = dispatch_outbox(limit=10)
    assert out["ok"] is True
    assert out["stub_sent"] == 1

    with SessionLocal() as db:
        m = db.query(OutboxMessage).filter(OutboxMessage.id == msg_id).one()
        assert m.status == "STUB_SENT"
        assert m.meta.get("preview", {}).get("document_id")

        doc = db.query(Document).filter(Document.id == m.meta["preview"]["document_id"]).one()
        assert doc.doc_type == "outbox_preview"
        assert "Outbox Preview" in (doc.content_text or "")


def test_outbox_dispatcher_is_idempotent(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")

    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import OutboxMessage, Tenant
    from app.tasks.jarvis_tasks import dispatch_outbox
    from app.util.ids import new_uuid
    from app.util.time import now_utc
    from tests.utils_bootstrap import seed_min_bootstrap_docs

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        seed_min_bootstrap_docs(db, tenant_id=tenant_id)
        msg_id = new_uuid()
        db.add(
            OutboxMessage(
                id=msg_id,
                tenant_id=tenant_id,
                user_id="u1",
                channel="stub",
                to="y",
                subject=None,
                body="b",
                meta={},
                status="QUEUED",
                created_at=now_utc(),
                sent_at=None,
            )
        )
        db.commit()

    out1 = dispatch_outbox(limit=10)
    out2 = dispatch_outbox(limit=10)

    assert out1["stub_sent"] == 1
    assert out2["stub_sent"] == 0
