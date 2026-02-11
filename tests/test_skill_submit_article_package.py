from __future__ import annotations


def test_skill_submit_article_package_blocked_without_manuscript(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")

    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import Task, Tenant
    from app.skills.runner import run_skill
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        db.commit()

        res = run_skill(db, tenant_id=tenant_id, user_id="u1", skill_name="submit_article_package", inputs={})
        assert res.status == "BLOCKED"
        assert res.created_task_ids

        count = db.query(Task).filter(Task.tenant_id == tenant_id).count()
        assert count >= 1


def test_skill_submit_article_package_creates_outbox_and_pending_action(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")

    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import PendingAction, Tenant
    from app.skills.runner import run_skill
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        db.commit()

        res = run_skill(
            db,
            tenant_id=tenant_id,
            user_id="u1",
            skill_name="submit_article_package",
            inputs={"manuscript_object_key": "t/x/manuscript.pdf", "editor_email": "editor@journal.org"},
        )
        assert res.status == "DONE"
        assert res.outbox_ids
        assert res.pending_action_ids

        pa = db.query(PendingAction).filter(PendingAction.id == res.pending_action_ids[0]).one()
        assert pa.action_type == "outbox.send"
