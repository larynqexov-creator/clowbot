from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
from app.core.db import SessionLocal
from app.skills.runner import run_skill

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/run")
def skills_run(payload: dict, ctx=Depends(get_ctx), db: Session = Depends(get_db)) -> dict:
    tenant_id, user_id = ctx
    skill_name = (payload or {}).get("skill_name")
    inputs = (payload or {}).get("inputs") or {}
    res = run_skill(db, tenant_id=tenant_id, user_id=user_id, skill_name=skill_name, inputs=inputs)
    return {
        "status": res.status,
        "reason": res.reason,
        "artifacts": res.artifacts,
        "created_task_ids": res.created_task_ids,
        "outbox_ids": res.outbox_ids,
        "pending_action_ids": res.pending_action_ids,
        "confirmation_tokens": res.confirmation_tokens,
    }
