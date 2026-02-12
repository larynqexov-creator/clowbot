from __future__ import annotations

import pytest


def _seed(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")

    # Settings object may already be imported; tests should override runtime values explicitly.
    from app.core.config import settings

    settings.OUTBOX_REAL_SEND_ENABLED = False
    settings.GITHUB_TOKEN = None
    settings.GITHUB_API_BASE = "https://api.github.com"


def test_outbox_github_dry_run_without_token(monkeypatch):
    _seed(monkeypatch)
    from app.core.config import settings

    settings.OUTBOX_REAL_SEND_ENABLED = True
    settings.GITHUB_TOKEN = None

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
        # allowlist repo
        db.add(
            Document(
                id=new_uuid(),
                tenant_id=tenant_id,
                workflow_id=None,
                domain="policy",
                doc_type="policy_allowlist",
                title="policy_allowlist",
                content_text=None,
                object_key=None,
                meta={"allowlist": {"github_repos": ["o/r"], "telegram_chats": [], "email_domains": [], "emails": []}},
                created_at=now_utc(),
            )
        )
        payload = {
            "schema": "clowbot.outbox.v1",
            "kind": "github_issue",
            "idempotency_key": "x",
            "context": {},
            "policy": {"risk": "YELLOW", "requires_approval": False, "allowlist": {"github_repos": []}},
            "message": {"repo": "o/r", "title": "t", "body": {"markdown": "b"}, "labels": [], "assignees": []},
            "attachments": [],
        }
        db.add(
            OutboxMessage(
                id=new_uuid(),
                tenant_id=tenant_id,
                user_id="u1",
                channel="github_issue",
                to="o/r",
                subject="t",
                body="b",
                payload=payload,
                idempotency_key="x",
                meta={},
                status="QUEUED",
                created_at=now_utc(),
                sent_at=None,
            )
        )
        db.commit()

    out = dispatch_outbox(limit=10)
    assert out["ok"] is True

    with SessionLocal() as db:
        m = db.query(OutboxMessage).filter(OutboxMessage.tenant_id == tenant_id).one()
        assert m.status == "DRY_RUN_SENT"


def test_outbox_github_real_send_mocked(monkeypatch):
    _seed(monkeypatch)
    from app.core.config import settings

    settings.OUTBOX_REAL_SEND_ENABLED = True
    settings.GITHUB_TOKEN = "tok"

    calls = {"n": 0}

    import httpx

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["n"] += 1

        class R:
            status_code = 201

            def json(self):
                return {"number": 12, "html_url": "https://github.com/o/r/issues/12", "id": 999, "title": json.get("title")}

            text = ""

        return R()

    monkeypatch.setattr(httpx, "post", fake_post)

    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import Document, OutboxMessage, Tenant
    from app.tasks.jarvis_tasks import dispatch_outbox
    from app.util.ids import new_uuid
    from app.util.time import now_utc
    from tests.utils_bootstrap import seed_min_bootstrap_docs

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    outbox_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        seed_min_bootstrap_docs(db, tenant_id=tenant_id)
        db.add(
            Document(
                id=new_uuid(),
                tenant_id=tenant_id,
                workflow_id=None,
                domain="policy",
                doc_type="policy_allowlist",
                title="policy_allowlist",
                content_text=None,
                object_key=None,
                meta={"allowlist": {"github_repos": ["o/r"], "telegram_chats": [], "email_domains": [], "emails": []}},
                created_at=now_utc(),
            )
        )
        payload = {
            "schema": "clowbot.outbox.v1",
            "kind": "github_issue",
            "idempotency_key": "x",
            "context": {},
            "policy": {"risk": "YELLOW", "requires_approval": False, "allowlist": {"github_repos": []}},
            "message": {"repo": "o/r", "title": "t", "body": {"markdown": "b"}, "labels": [], "assignees": []},
            "attachments": [],
        }
        db.add(
            OutboxMessage(
                id=outbox_id,
                tenant_id=tenant_id,
                user_id="u1",
                channel="github_issue",
                to="o/r",
                subject="t",
                body="b",
                payload=payload,
                idempotency_key="x",
                meta={},
                status="QUEUED",
                created_at=now_utc(),
                sent_at=None,
            )
        )
        db.commit()

    out = dispatch_outbox(limit=10)
    assert out["ok"] is True

    with SessionLocal() as db:
        m = db.query(OutboxMessage).filter(OutboxMessage.id == outbox_id).one()
        assert m.status == "SENT"
        assert m.meta.get("external", {}).get("url")

    assert calls["n"] == 1


def test_outbox_github_requires_approval_when_not_allowlisted(monkeypatch):
    _seed(monkeypatch)
    from app.core.config import settings

    settings.OUTBOX_REAL_SEND_ENABLED = True
    settings.GITHUB_TOKEN = "tok"

    import httpx

    def boom(*args, **kwargs):
        raise AssertionError("should not send when not allowlisted")

    monkeypatch.setattr(httpx, "post", boom)

    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import Document, OutboxMessage, Tenant
    from app.tasks.jarvis_tasks import dispatch_outbox
    from app.util.ids import new_uuid
    from app.util.time import now_utc
    from tests.utils_bootstrap import seed_min_bootstrap_docs

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    outbox_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        seed_min_bootstrap_docs(db, tenant_id=tenant_id)
        # allowlist is empty (repo NOT allowlisted)
        db.add(
            Document(
                id=new_uuid(),
                tenant_id=tenant_id,
                workflow_id=None,
                domain="policy",
                doc_type="policy_allowlist",
                title="policy_allowlist",
                content_text=None,
                object_key=None,
                meta={"allowlist": {"github_repos": [], "telegram_chats": [], "email_domains": [], "emails": []}},
                created_at=now_utc(),
            )
        )
        payload = {
            "schema": "clowbot.outbox.v1",
            "kind": "github_issue",
            "idempotency_key": "x",
            "context": {},
            "policy": {"risk": "YELLOW", "requires_approval": False, "allowlist": {"github_repos": []}},
            "message": {"repo": "o/r", "title": "t", "body": {"markdown": "b"}, "labels": [], "assignees": []},
            "attachments": [],
        }
        db.add(
            OutboxMessage(
                id=outbox_id,
                tenant_id=tenant_id,
                user_id="u1",
                channel="github_issue",
                to="o/r",
                subject="t",
                body="b",
                payload=payload,
                idempotency_key="x",
                meta={},
                status="QUEUED",
                created_at=now_utc(),
                sent_at=None,
            )
        )
        db.commit()

    out = dispatch_outbox(limit=10)
    assert out["ok"] is True

    with SessionLocal() as db:
        m = db.query(OutboxMessage).filter(OutboxMessage.id == outbox_id).one()
        assert m.status == "QUEUED"
        assert (m.payload or {}).get("policy", {}).get("requires_approval") is True
