from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import require_admin_token
from app.models.tables import Document
from app.policy.allowlist import load_policy_allowlist
from app.schemas.outbox_v1 import Allowlist
from app.util.ids import new_uuid
from app.util.time import now_utc

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/allowlist", dependencies=[Depends(require_admin_token)])
def get_allowlist(tenant_id: str, db: Session = Depends(get_db)) -> dict:
    doc = load_policy_allowlist(db, tenant_id=tenant_id)
    return {"tenant_id": tenant_id, "document_id": doc.document_id, "allowlist": doc.allowlist.model_dump()}


@router.put("/allowlist", dependencies=[Depends(require_admin_token)])
def put_allowlist(tenant_id: str, payload: dict, db: Session = Depends(get_db)) -> dict:
    allow = Allowlist.model_validate((payload or {}).get("allowlist") or payload or {})

    doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="policy",
        doc_type="policy_allowlist",
        title="policy_allowlist",
        content_text=None,
        object_key=None,
        meta={"allowlist": allow.model_dump()},
        created_at=now_utc(),
    )
    db.add(doc)
    db.commit()
    return {"tenant_id": tenant_id, "document_id": doc.id, "allowlist": allow.model_dump()}
