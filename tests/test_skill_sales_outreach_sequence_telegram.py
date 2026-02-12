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

    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import Tenant
    from tests.utils_bootstrap import seed_min_bootstrap_docs
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    import app.main

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()

    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        seed_min_bootstrap_docs(db, tenant_id=tenant_id)
        db.commit()

    c = TestClient(app.main.app)
    c.headers.update({"X-Tenant-Id": tenant_id, "X-User-Id": "u1"})
    return c


def test_sales_outreach_sequence_queues_telegram_outbox_items(client: TestClient):
    r = client.post(
        "/skills/run",
        json={
            "skill_name": "sales_outreach_sequence",
            "inputs": {"product": "X", "audience": "Y", "chat_id": "123", "count": 3},
        },
    )
    assert r.status_code == 200
    data = r.json()

    assert data["status"] == "DONE"
    assert len(data["outbox_ids"]) == 3
    assert "offer_doc_id" in data["artifacts"]
