from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
from app.api.guards import require_bootstrap
from app.core.db import SessionLocal
from app.models.tables import Document
from app.util.ids import new_uuid
from app.util.time import now_utc

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/overview")
def mindmap_overview() -> dict:
    mermaid = """flowchart TD
  A[Clowbot]:::doing
  A --> B[MVP baseline]:::doing
  B --> B1[Tenants + Grants workflow]:::done
  B --> B2[Memory notes + search]:::doing
  B --> B3[Mindmap endpoints]:::doing
  A --> J[Jarvis layer]:::doing
  J --> J2[Approvals Queue]:::doing
  J --> J3[Outbox]:::doing
  J --> J4[Custom Mindmaps]:::doing

  classDef done fill:#b7f7c5,stroke:#1f7a2e,color:#000;
  classDef doing fill:#ffe8a3,stroke:#8a6d00,color:#000;
  classDef todo fill:#e6e6e6,stroke:#666,color:#000;
"""
    return {"mermaid": mermaid}


@router.post("/custom")
def create_custom_mindmap(payload: dict, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, user_id = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    title = (payload or {}).get("title") or "Custom mindmap"
    mermaid = (payload or {}).get("mermaid")
    if not mermaid:
        return {"detail": "Missing mermaid"}

    doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="mindmap",
        doc_type="mindmap_custom",
        title=title,
        content_text=mermaid,
        object_key=None,
        meta={"created_by": user_id},
        created_at=now_utc(),
    )
    db.add(doc)
    db.commit()

    return {"id": doc.id, "title": doc.title}


@router.get("/custom/latest")
def get_custom_mindmap_latest(ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, _ = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    doc: Document | None = (
        db.query(Document)
        .filter(
            Document.tenant_id == tenant_id,
            Document.domain == "mindmap",
            Document.doc_type == "mindmap_custom",
        )
        .order_by(Document.created_at.desc())
        .limit(1)
        .one_or_none()
    )

    if not doc:
        return {"id": None, "title": None, "mermaid": None}

    return {"id": doc.id, "title": doc.title, "mermaid": doc.content_text, "created_at": doc.created_at}


@router.get("/project/{project_id}")
def get_project_mindmap(project_id: str, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, _ = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    doc: Document | None = (
        db.query(Document)
        .filter(
            Document.tenant_id == tenant_id,
            Document.domain == "mindmap",
            Document.doc_type == "project_mindmap",
        )
        .order_by(Document.created_at.desc())
        .limit(50)
        .all()
    )

    picked: Document | None = None
    for d in doc or []:
        if (d.meta or {}).get("project_id") == project_id:
            picked = d
            break

    if not picked:
        raise HTTPException(status_code=404, detail="Project mindmap not found")

    return {
        "project_id": project_id,
        "document_id": picked.id,
        "mermaid": picked.content_text,
        "map_index": (picked.meta or {}).get("map_index") or {},
        "created_at": picked.created_at,
    }
