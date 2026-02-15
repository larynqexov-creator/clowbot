from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
# require_bootstrap intentionally not used for /inbox endpoints
from app.core.db import SessionLocal
from app.memory.object_store import put_bytes
from app.models.tables import InboxItem
from app.project_library.service import create_inbox_file_records, create_inbox_text, refresh_project_library, resolve_project
from app.tasks.inbox_tasks import process_inbox_item

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    # Accept CSV or JSON-ish bracketed list; keep it simple.
    parts = [p.strip() for p in raw.replace("[", "").replace("]", "").split(",")]
    return [p for p in parts if p]


@router.post("/text")
def inbox_text(payload: dict, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, user_id = ctx
    # Inbox is a "simple entry" channel: do NOT hard-block on bootstrap.
    # Bootstrap freshness gates should apply to skills/task execution, not capture.

    project_id = (payload or {}).get("project_id")
    project_slug = (payload or {}).get("project_slug")
    project_tag = (payload or {}).get("project_tag")
    if not project_slug and project_tag:
        project_slug = project_tag
    title = (payload or {}).get("title")
    text = (payload or {}).get("text")
    tags = (payload or {}).get("tags") or []
    source = (payload or {}).get("source") or "api"

    if not text:
        raise HTTPException(status_code=400, detail="Missing text")

    proj = resolve_project(db, tenant_id=tenant_id, project_id=project_id, project_slug=project_slug)

    item = create_inbox_text(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        project=proj,
        title=title,
        text=text,
        tags=tags,
        source=source,
    )

    return {"id": item.id, "status": item.status, "project_id": item.project_id}


@router.post("/file")
async def inbox_file(
    ctx=Depends(get_ctx),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    project_id: str | None = Form(default=None),
    project_slug: str | None = Form(default=None),
    project_tag: str | None = Form(default=None),
    title: str | None = Form(default=None),
    tags: str | None = Form(default=None),
    source: str | None = Form(default="api"),
) -> dict:
    tenant_id, user_id = ctx
    # Inbox is a "simple entry" channel: do NOT hard-block on bootstrap.
    # Bootstrap freshness gates should apply to skills/task execution, not capture.

    if not project_slug and project_tag:
        project_slug = project_tag

    proj = resolve_project(db, tenant_id=tenant_id, project_id=project_id, project_slug=project_slug)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    content_type = file.content_type or "application/octet-stream"

    item, asset, asset_meta_doc = create_inbox_file_records(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        project=proj,
        title=title,
        filename=file.filename or "upload.bin",
        content_type=content_type,
        data=data,
        tags=_parse_tags(tags),
        source=source or "api",
    )

    # Store bytes (best-effort)
    put_bytes(object_key=item.object_key or "", data=data, content_type=content_type)

    # Enqueue processing.
    # NOTE: Celery eager mode can be affected by import order; to keep unit tests deterministic
    # we run inline when CELERY_TASK_ALWAYS_EAGER is enabled.
    try:
        from app.core.config import settings

        if settings.CELERY_TASK_ALWAYS_EAGER:
            process_inbox_item(item.id)
        else:
            process_inbox_item.delay(item.id)
    except Exception:
        pass

    return {
        "inbox_item_id": item.id,
        "project_id": item.project_id,
        "asset_id": (asset.id if asset else None),
        "object_key": item.object_key,
        "status": item.status,
    }


@router.get("/unassigned")
def inbox_unassigned(ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, _ = ctx
    # Inbox is a "simple entry" channel: do NOT hard-block on bootstrap.

    items = (
        db.query(InboxItem)
        .filter(InboxItem.tenant_id == tenant_id, InboxItem.project_id.is_(None))
        .order_by(InboxItem.created_at.desc())
        .limit(200)
        .all()
    )
    return {
        "items": [
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
            for it in items
        ]
    }
