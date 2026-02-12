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
    from app.models.tables import Task, Tenant
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    import app.main

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    task_id = new_uuid()

    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        db.add(
            Task(
                id=task_id,
                tenant_id=tenant_id,
                workflow_id=None,
                title="Run article submit skill",
                status="TODO",
                meta={"task_type": "ARTICLE", "inputs": {"manuscript_object_key": "obj://m", "editor_email": "ed@example.com", "journal_name": "J"}},
                created_at=now_utc(),
            )
        )
        db.commit()

    c = TestClient(app.main.app)
    c.headers.update({"X-Tenant-Id": tenant_id, "X-User-Id": "u1"})
    c._task_id = task_id  # type: ignore[attr-defined]
    return c


def test_tasks_run_skill_uses_tasktype_binding(client: TestClient):
    task_id = client._task_id  # type: ignore[attr-defined]

    r = client.post(f"/tasks/{task_id}/run_skill", json={})
    assert r.status_code == 200
    data = r.json()

    assert data["task_id"] == task_id
    assert data["task_type"] == "ARTICLE"
    assert data["skill_name"] == "submit_article_package"
    # submit_article_package should create a RED pending action (approval required)
    assert data["status"] in {"DONE", "BLOCKED"}
    assert isinstance(data["pending_action_ids"], list)
