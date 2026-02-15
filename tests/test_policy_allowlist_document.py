from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")

    import app.main
    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import Document, Tenant
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()

    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        # tenant-wide allowlist document
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
                meta={"allowlist": {"telegram_chats": ["123"], "email_domains": [], "emails": [], "github_repos": []}},
                created_at=now_utc(),
            )
        )
        db.commit()

    c = TestClient(app.main.app)
    c.headers.update({"X-Tenant-Id": tenant_id, "X-User-Id": "u1"})
    c._tenant_id = tenant_id  # type: ignore[attr-defined]
    return c


def test_tenant_allowlist_document_is_merged_into_payload_allowlist(client: TestClient):
    # /tools/telegram/send creates an outbox message and triggers allowlist enforcement.
    # We pass an empty per-request allowlist, but the tenant policy document allowlists chat_id=123.
    r = client.post(
        "/tools/telegram/send",
        json={"to": "123", "text": "hi", "allowlist": {"telegram_chats": []}},
    )
    assert r.status_code == 200

    data = r.json()
    # should not require approval (tenant allowlist allows chat 123)
    assert data["pending_action_id"] is None
    assert isinstance(data["outbox_id"], str)
