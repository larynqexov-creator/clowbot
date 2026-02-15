from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_memory_bootstrap import _write_sot


# Minimal PDF containing the text "Hello ClowBot".
# Generated once and embedded to avoid extra deps.
MINI_PDF = (
    b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 59 >>\nstream\nBT\n/F1 18 Tf\n72 72 Td\n(Hello ClowBot) Tj\nET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000015 00000 n \n0000000064 00000 n \n0000000121 00000 n \n0000000277 00000 n \n0000000402 00000 n \n"
    b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n492\n%%EOF\n"
)


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
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")

    # Local object store for tests
    monkeypatch.setenv("LOCAL_OBJECT_STORE_DIR", str(tmp_path / "obj"))

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
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.LOCAL_OBJECT_STORE_DIR = str(tmp_path / "obj")

    Base.metadata.create_all(bind=engine)

    tenant_id = new_uuid()
    with SessionLocal() as db:
        db.add(Tenant(id=tenant_id, name=f"t-{tenant_id}", created_at=now_utc()))
        db.commit()

    c = TestClient(app.main.app)
    c.headers.update({"X-Tenant-Id": tenant_id, "X-User-Id": "u1"})
    c._tenant_id = tenant_id  # type: ignore[attr-defined]
    return c


def test_capture_text_updates_library_and_mindmap(client: TestClient):
    # bootstrap required
    r = client.post("/memory/bootstrap")
    assert r.status_code == 200

    p = client.post("/projects", json={"slug": "hockey", "title": "Hockey"}).json()
    pid = p["id"]

    r2 = client.post(
        "/inbox/text",
        json={"project_id": pid, "title": "note1", "text": "hello from inbox", "tags": ["t1"], "source": "api"},
    )
    assert r2.status_code == 200

    idx = client.get(f"/projects/{pid}/library/index")
    assert idx.status_code == 200
    assert "text/markdown" in (idx.headers.get("content-type") or "")
    assert "Project library" in (idx.text or "")

    mm = client.get(f"/mindmap/project/{pid}")
    assert mm.status_code == 200
    mermaid = mm.json().get("mermaid") or ""
    assert "Assets" in mermaid
    assert "click" in mermaid


def test_capture_pdf_extracts_text_and_updates_mindmap_index(client: TestClient):
    r = client.post("/memory/bootstrap")
    assert r.status_code == 200

    p = client.post("/projects", json={"slug": "hockey", "title": "Hockey"}).json()
    pid = p["id"]

    files = {"file": ("demo.pdf", MINI_PDF, "application/pdf")}
    r2 = client.post(f"/inbox/file?", files=files, data={"project_id": pid, "title": "deck", "tags": "deck"})
    assert r2.status_code == 200
    inbox_item_id = r2.json()["inbox_item_id"]

    # extracted_text doc exists
    from app.core.db import SessionLocal
    from app.models.tables import Document, InboxItem

    with SessionLocal() as db:
        it = db.query(InboxItem).filter(InboxItem.id == inbox_item_id).one()
        assert it.status in {"DONE", "QUEUED"}  # eager should make it DONE
        docs = (
            db.query(Document)
            .filter(Document.tenant_id == client._tenant_id)  # type: ignore[attr-defined]
            .filter(Document.doc_type == "extracted_text")
            .all()
        )
        assert any((d.content_text or "").find("Hello ClowBot") >= 0 for d in docs)

    mm = client.get(f"/mindmap/project/{pid}")
    assert mm.status_code == 200
    mermaid = mm.json().get("mermaid") or ""
    assert "click" in mermaid
    assert isinstance(mm.json().get("map_index"), dict)
