from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tables import Document
from app.util.ids import new_uuid
from app.util.time import now_utc


def seed_min_bootstrap_docs(db: Session, *, tenant_id: str) -> None:
    """Insert minimal SoT docs so BOOTSTRAP_REQUIRED guard passes in unit tests."""

    now = now_utc()
    for doc_type, title, content in [
        ("mission", "mission", "# mission\n"),
        ("status", "status", "# status\n"),
        ("next", "next", "# next\n"),
    ]:
        db.add(
            Document(
                id=new_uuid(),
                tenant_id=tenant_id,
                workflow_id=None,
                domain="sot",
                doc_type=doc_type,
                title=title,
                content_text=content,
                object_key=None,
                meta={"content_sha256": "test", "refreshed_at": now.isoformat(), "source_path": f"{doc_type}.md"},
                created_at=now,
            )
        )
