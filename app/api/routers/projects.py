from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
from app.api.guards import require_bootstrap
from app.core.db import SessionLocal
from app.models.tables import Project, ProjectDecision
from app.project_library.service import refresh_project_library, resolve_project
from app.util.ids import new_uuid
from app.util.time import now_utc

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("")
def create_project_endpoint(payload: dict, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, user_id = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    slug = (payload or {}).get("slug")
    title = (payload or {}).get("title")
    if not slug or not title:
        raise HTTPException(status_code=400, detail="Missing slug/title")

    existing = resolve_project(db, tenant_id=tenant_id, project_slug=slug)
    if existing:
        raise HTTPException(status_code=409, detail="Project slug already exists")

    p = Project(id=new_uuid(), tenant_id=tenant_id, slug=slug, title=title, status="ACTIVE", created_at=now_utc())
    db.add(p)
    db.commit()

    refresh_project_library(db, tenant_id=tenant_id, project_id=p.id)

    return {"id": p.id, "slug": p.slug, "title": p.title, "status": p.status}


@router.get("")
def list_projects(ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, _ = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    items = (
        db.query(Project)
        .filter(Project.tenant_id == tenant_id)
        .order_by(Project.created_at.desc())
        .limit(200)
        .all()
    )
    return {
        "projects": [
            {"id": p.id, "slug": p.slug, "title": p.title, "status": p.status, "created_at": p.created_at}
            for p in items
        ]
    }


@router.post("/{project_id}/decisions")
def add_decision(project_id: str, payload: dict, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, user_id = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    proj = resolve_project(db, tenant_id=tenant_id, project_id=project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    title = (payload or {}).get("title")
    # v1 accepts either {decision: str} or {markdown: str} for the main body.
    decision = (payload or {}).get("decision") or (payload or {}).get("markdown")
    rationale = (payload or {}).get("rationale")
    links = (payload or {}).get("links") or []

    if not title:
        title = "Decision"

    if not decision:
        raise HTTPException(status_code=400, detail="Missing decision/markdown")

    d = ProjectDecision(
        id=new_uuid(),
        tenant_id=tenant_id,
        project_id=project_id,
        title=title,
        decision=decision,
        rationale=rationale,
        links=links,
        created_at=now_utc(),
    )
    db.add(d)
    db.commit()

    refresh_project_library(db, tenant_id=tenant_id, project_id=project_id)

    return {"id": d.id, "title": d.title, "project_id": d.project_id}


@router.get("/{project_id}/decisions/{decision_id}")
def get_decision_markdown(
    project_id: str, decision_id: str, ctx=Depends(get_ctx), db: Session = Depends(get_db)
) -> Response:
    tenant_id, _ = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    proj = resolve_project(db, tenant_id=tenant_id, project_id=project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    d: ProjectDecision | None = (
        db.query(ProjectDecision)
        .filter(
            ProjectDecision.tenant_id == tenant_id,
            ProjectDecision.project_id == project_id,
            ProjectDecision.id == decision_id,
        )
        .one_or_none()
    )
    if not d:
        raise HTTPException(status_code=404, detail="Decision not found")

    md = f"# {d.title}\n\n" + (d.decision or "") + "\n"
    if d.rationale:
        md += f"\n## Rationale\n\n{d.rationale}\n"
    if d.links:
        md += "\n## Links\n\n" + "\n".join([f"- {x}" for x in d.links]) + "\n"

    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")


@router.get("/{project_id}/assets/{asset_id}/preview")
def preview_asset(project_id: str, asset_id: str, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> Response:
    tenant_id, _ = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    proj = resolve_project(db, tenant_id=tenant_id, project_id=project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.models.tables import ProjectAsset

    a: ProjectAsset | None = (
        db.query(ProjectAsset)
        .filter(ProjectAsset.tenant_id == tenant_id, ProjectAsset.project_id == project_id, ProjectAsset.id == asset_id)
        .one_or_none()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Asset not found")

    from app.memory.object_store import get_bytes

    data = get_bytes(object_key=a.object_key or "") or b""
    if not data:
        raise HTTPException(status_code=404, detail="Asset bytes not found")

    return Response(content=data, media_type=a.content_type or "application/octet-stream")


@router.get("/{project_id}/library")
def get_project_library(project_id: str, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, _ = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    proj = resolve_project(db, tenant_id=tenant_id, project_id=project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.models.tables import InboxItem, ProjectAsset, Document

    inbox = (
        db.query(InboxItem)
        .filter(InboxItem.tenant_id == tenant_id, InboxItem.project_id == project_id)
        .order_by(InboxItem.created_at.desc())
        .limit(200)
        .all()
    )
    assets = (
        db.query(ProjectAsset)
        .filter(ProjectAsset.tenant_id == tenant_id, ProjectAsset.project_id == project_id)
        .order_by(ProjectAsset.created_at.desc())
        .limit(200)
        .all()
    )
    decisions = (
        db.query(ProjectDecision)
        .filter(ProjectDecision.tenant_id == tenant_id, ProjectDecision.project_id == project_id)
        .order_by(ProjectDecision.created_at.desc())
        .limit(200)
        .all()
    )

    # Latest index doc
    # SQLite JSON filtering is not always available; resolve in Python.
    candidates = (
        db.query(Document)
        .filter(Document.tenant_id == tenant_id, Document.domain == "project", Document.doc_type == "project_library_index")
        .order_by(Document.created_at.desc())
        .limit(50)
        .all()
    )
    idx: Document | None = None
    for c in candidates:
        if (c.meta or {}).get("project_id") == project_id:
            idx = c
            break

    return {
        "project": {"id": proj.id, "slug": proj.slug, "title": proj.title, "status": proj.status},
        "inbox_items": [
            {
                "id": it.id,
                "kind": it.kind,
                "title": it.title,
                "status": it.status,
                "content_type": it.content_type,
                "object_key": it.object_key,
                "tags": it.tags,
                "source": it.source,
                "created_at": it.created_at,
            }
            for it in inbox
        ],
        "assets": [
            {
                "id": a.id,
                "filename": a.filename,
                "content_type": a.content_type,
                "object_key": a.object_key,
                "sha256": a.sha256,
                "size_bytes": a.size_bytes,
                "created_at": a.created_at,
            }
            for a in assets
        ],
        "decisions": [
            {
                "id": d.id,
                "title": d.title,
                "decision": d.decision,
                "rationale": d.rationale,
                "links": d.links,
                "created_at": d.created_at,
            }
            for d in decisions
        ],
        "index_document": {"id": idx.id, "created_at": idx.created_at} if idx else None,
    }


@router.get("/{project_id}/library/index")
def get_project_library_index(project_id: str, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> Response:
    tenant_id, _ = ctx
    require_bootstrap(db, tenant_id=tenant_id)

    proj = resolve_project(db, tenant_id=tenant_id, project_id=project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.models.tables import Document

    candidates = (
        db.query(Document)
        .filter(Document.tenant_id == tenant_id, Document.domain == "project", Document.doc_type == "project_library_index")
        .order_by(Document.created_at.desc())
        .limit(50)
        .all()
    )
    doc: Document | None = None
    for c in candidates:
        if (c.meta or {}).get("project_id") == project_id:
            doc = c
            break
    if not doc:
        raise HTTPException(status_code=404, detail="Index not found")

    return PlainTextResponse(doc.content_text or "", media_type="text/markdown; charset=utf-8")
