from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.domain.science.grants.workflow import start_grants_workflow
from app.models.tables import Workflow

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_ctx(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id")
    if not x_user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id")
    return x_tenant_id, x_user_id


@router.post("/run")
def run_grants(ctx=Depends(get_ctx), db: Session = Depends(get_db)):
    tenant_id, user_id = ctx
    wf_id = start_grants_workflow(db=db, tenant_id=tenant_id, user_id=user_id)
    return {"workflow_id": wf_id}


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str, ctx=Depends(get_ctx), db: Session = Depends(get_db)):
    tenant_id, _ = ctx
    wf: Workflow | None = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
        .one_or_none()
    )
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": wf.id,
        "tenant_id": wf.tenant_id,
        "domain": wf.domain,
        "type": wf.type,
        "status": wf.status,
        "state": wf.state,
        "artifacts": wf.artifacts,
        "last_error": wf.last_error,
        "created_at": wf.created_at,
        "updated_at": wf.updated_at,
    }
