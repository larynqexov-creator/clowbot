from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
from app.core.db import SessionLocal
from app.memory.bootstrap import bootstrap_status, refresh_bootstrap

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/bootstrap")
def post_bootstrap(ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, user_id = ctx
    return refresh_bootstrap(db, tenant_id=tenant_id, user_id=user_id)


@router.get("/bootstrap/status")
def get_bootstrap_status(ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, _ = ctx
    return bootstrap_status(db, tenant_id=tenant_id)


@router.get("/next")
def get_next(ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    """Convenience endpoint for NEXT.md (after bootstrap)."""

    tenant_id, _ = ctx
    from app.models.tables import Document

    doc: Document | None = (
        db.query(Document)
        .filter(Document.tenant_id == tenant_id, Document.domain == "sot", Document.doc_type == "next")
        .order_by(Document.created_at.desc())
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="NEXT not found (run /memory/bootstrap)")

    return {"tenant_id": tenant_id, "document_id": doc.id, "content_text": doc.content_text, "meta": doc.meta}
