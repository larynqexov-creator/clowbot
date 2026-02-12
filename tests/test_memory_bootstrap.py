from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _write_sot(tmp: Path, *, next_text: str = "# NEXT\n") -> None:
    (tmp / "CLOWDBOT_SUPERMISSION.md").write_text("# MISSION\n", encoding="utf-8")
    (tmp / "STATUS.md").write_text("# STATUS\n", encoding="utf-8")
    (tmp / "MINDMAP.md").write_text("# MINDMAP\n", encoding="utf-8")
    (tmp / "BOOTSTRAP.md").write_text("# BOOTSTRAP\n", encoding="utf-8")
    (tmp / "BACKLOG.md").write_text("# BACKLOG\n", encoding="utf-8")
    (tmp / "NEXT.md").write_text(next_text, encoding="utf-8")


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("ADMIN_TOKEN", "change-me-admin-token")
    monkeypatch.setenv("ENSURE_EXTERNAL_DEPS_ON_STARTUP", "0")

    # SoT root
    _write_sot(tmp_path)
    monkeypatch.setenv("SOT_ROOT_DIR", str(tmp_path))
    monkeypatch.setenv("BOOTSTRAP_MAX_AGE_HOURS", "24")

    from app.core.db import SessionLocal, engine
    from app.models.base import Base
    from app.models.tables import Tenant
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    import app.main

    # Settings object may already be imported by other tests; enforce runtime overrides.
    from app.core.config import settings

    settings.SOT_ROOT_DIR = str(tmp_path)
    settings.BOOTSTRAP_MAX_AGE_HOURS = 24

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        db.commit()

    c = TestClient(app.main.app)
    c.headers.update({"X-Tenant-Id": tenant_id, "X-User-Id": "u1"})
    c._tenant_id = tenant_id  # type: ignore[attr-defined]
    c._tmp_path = tmp_path  # type: ignore[attr-defined]
    return c


def test_bootstrap_refresh_creates_documents(client: TestClient):
    r = client.post("/memory/bootstrap")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["context_version"]

    st = client.get("/memory/bootstrap/status")
    assert st.status_code == 200
    sdata = st.json()

    doc_types = {x["doc_type"] for x in sdata["sources"] if x.get("document_id")}
    assert {"mission", "status", "next", "backlog", "mindmap_dev", "bootstrap"}.issubset(doc_types)


def test_bootstrap_guard_blocks_skill_without_bootstrap(client: TestClient):
    # New tenant without SoT docs
    from app.core.db import SessionLocal
    from app.models.tables import Tenant
    from app.util.ids import new_uuid
    from app.util.time import now_utc

    tenant2 = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant2, name=f"t-{tenant2}", created_at=now_utc()))
        db.commit()

    client.headers.update({"X-Tenant-Id": tenant2, "X-User-Id": "u1"})

    r = client.post("/skills/run", json={"skill_name": "weekly_review", "inputs": {"portfolio_markdown": "x"}})
    assert r.status_code == 409
    detail = r.json().get("detail")
    assert detail["code"] == "BOOTSTRAP_REQUIRED"


def test_context_version_stable_and_changes_on_file_change(client: TestClient):
    r1 = client.post("/memory/bootstrap").json()
    r2 = client.post("/memory/bootstrap").json()
    assert r1["context_version"] == r2["context_version"]

    tmp_path: Path = client._tmp_path  # type: ignore[attr-defined]
    (tmp_path / "NEXT.md").write_text("# NEXT\nchanged\n", encoding="utf-8")

    r3 = client.post("/memory/bootstrap").json()
    assert r3["context_version"] != r2["context_version"]
