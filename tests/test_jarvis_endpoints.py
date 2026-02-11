from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    import app.main

    # Create schema (SQLite tests don't run Alembic).
    Base.metadata.create_all(bind=engine)

    # Seed tenant.
    with SessionLocal() as db:
        from app.models.tables import Tenant

        tenant_id = new_uuid()
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        db.commit()

    c = TestClient(app.main.app)
    c.headers.update({"X-Tenant-Id": tenant_id, "X-User-Id": "u1"})
    return c


def test_mindmap_overview(client: TestClient):
    r = client.get("/mindmap/overview")
    assert r.status_code == 200
    data = r.json()
    assert "mermaid" in data
    assert "flowchart" in data["mermaid"]


def test_custom_mindmap_roundtrip(client: TestClient):
    r = client.post("/mindmap/custom", json={"title": "X", "mermaid": "flowchart TD\nA-->B"})
    assert r.status_code == 200
    doc_id = r.json()["id"]
    assert doc_id

    latest = client.get("/mindmap/custom/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == doc_id
    assert latest.json()["mermaid"].startswith("flowchart")


def test_pending_action_approve_requires_token(client: TestClient):
    from app.core.db import SessionLocal
    from app.models.tables import PendingAction
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    action_id = new_uuid()
    token = "t-approve"

    with SessionLocal() as db:
        db.add(
            PendingAction(
                id=action_id,
                tenant_id=client.headers["X-Tenant-Id"],
                user_id=None,
                risk_level="RED",
                action_type="send_message",
                payload={"to": "someone", "body": "hi"},
                status="PENDING",
                confirmation_token_hash=_hash_token(token),
                created_at=now_utc(),
                decided_at=None,
            )
        )
        db.commit()

    bad = client.post(f"/actions/{action_id}/approve", json={"confirmation_token": "wrong"})
    assert bad.status_code == 403

    ok = client.post(f"/actions/{action_id}/approve", json={"confirmation_token": token})
    assert ok.status_code == 200
    assert ok.json()["status"] == "APPROVED"

    pending = client.get("/actions/pending")
    assert pending.status_code == 200
    ids = [x["id"] for x in pending.json()["items"]]
    assert action_id not in ids
