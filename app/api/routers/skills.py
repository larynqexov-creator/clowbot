from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
from app.api.guards import require_bootstrap
from app.core.db import SessionLocal
from app.models.tables import AuditLog
from app.skills.runner import run_skill
from app.util.ids import new_uuid
from app.util.time import now_utc

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

    context_version = require_bootstrap(db, tenant_id=tenant_id)

    skill_name = (payload or {}).get("skill_name")
    inputs = (payload or {}).get("inputs") or {}

    db.add(
        AuditLog(
            id=new_uuid(),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="SKILL_RUN_STARTED",
            severity="INFO",
            message=f"skill={skill_name}",
            context={"context_version": context_version, "skill_name": skill_name},
            created_at=now_utc(),
        )
    )
    db.commit()

    res = run_skill(db, tenant_id=tenant_id, user_id=user_id, skill_name=skill_name, inputs=inputs)
    db.commit()

    return {
        "status": res.status,
        "reason": res.reason,
        "context_version": context_version,
        "artifacts": res.artifacts,
        "created_task_ids": res.created_task_ids,
        "outbox_ids": res.outbox_ids,
        "pending_action_ids": res.pending_action_ids,
        "confirmation_tokens": res.confirmation_tokens,
    }
