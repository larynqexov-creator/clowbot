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
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    import app.main

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()

    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        db.commit()

    c = TestClient(app.main.app)
    c.headers.update({"X-Tenant-Id": tenant_id, "X-User-Id": "u1"})
    return c


def test_weekly_review_parses_portfolio_and_creates_tasks(client: TestClient):
    portfolio_md = """
| Project | Area | MoneyPotential | Urgency | Leverage | StrategicValue | RiskPenalty | Score | Status | Next Action | Owner |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| A | Business | 7 | 6 | 8 | 9 | 3 | 0 | ACTIVE | Do A | me |
| B | Science | 1 | 1 | 1 | 1 | 0 | 0 | PAUSED | Do B | me |
| C | Personal | 0 | 0 | 0 | 0 | 0 | 0 | DONE | Do C | me |
"""

    r = client.post(
        "/skills/run",
        json={"skill_name": "weekly_review", "inputs": {"portfolio_markdown": portfolio_md, "min_active": 1, "max_active": 2}},
    )
    assert r.status_code == 200
    data = r.json()

    assert data["status"] == "DONE"
    assert "weekly_review_doc_id" in data["artifacts"]
    # should create tasks for A and B (C is DONE)
    assert len(data["created_task_ids"]) == 2
