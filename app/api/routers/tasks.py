from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_ctx
from app.api.guards import require_bootstrap
from app.core.db import SessionLocal
from app.models.tables import AuditLog, Task
from app.skills.registry import TASKTYPE_TO_SKILL
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


def _audit(
    db: Session,
    *,
    tenant_id: str | None,
    user_id: str | None,
    event_type: str,
    severity: str,
    message: str,
    context: dict,
) -> None:
    db.add(
        AuditLog(
            id=new_uuid(),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            message=message,
            context=context or {},
            created_at=now_utc(),
        )
    )


@router.post("/{task_id}/run_skill")
def task_run_skill(
    task_id: str, payload: dict | None = None, ctx=Depends(get_ctx), db: Session = Depends(get_db)
) -> dict:
    """Run a skill bound to the task's TaskType.

    Binding rules:
    - task.meta.task_type (or task.meta.type) is looked up in TASKTYPE_TO_SKILL.
    - inputs come from request payload.inputs, falling back to task.meta.inputs.

    This endpoint is intended for the dispatcher/worker to reify tasks into skill runs.
    """

    tenant_id, user_id = ctx

    context_version = require_bootstrap(db, tenant_id=tenant_id)

    t: Task | None = db.query(Task).filter(Task.id == task_id, Task.tenant_id == tenant_id).one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")

    meta = dict(t.meta or {})
    task_type = (meta.get("task_type") or meta.get("type") or "").strip()
    if not task_type:
        raise HTTPException(status_code=409, detail="Task has no task_type in metadata")

    skill_name = TASKTYPE_TO_SKILL.get(task_type)
    if not skill_name:
        raise HTTPException(status_code=409, detail=f"No skill binding for task_type={task_type}")

    inputs = (payload or {}).get("inputs") or meta.get("inputs") or {}

    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="TASK_RUN_SKILL",
        severity="INFO",
        message=f"task={task_id} task_type={task_type} skill={skill_name}",
        context={
            "task_id": task_id,
            "task_type": task_type,
            "skill_name": skill_name,
            "context_version": context_version,
        },
    )
    db.commit()

    res = run_skill(db, tenant_id=tenant_id, user_id=user_id, skill_name=skill_name, inputs=inputs)
    db.commit()

    return {
        "task_id": task_id,
        "task_type": task_type,
        "skill_name": skill_name,
        "status": res.status,
        "reason": res.reason,
        "artifacts": res.artifacts,
        "created_task_ids": res.created_task_ids,
        "outbox_ids": res.outbox_ids,
        "pending_action_ids": res.pending_action_ids,
        "confirmation_tokens": res.confirmation_tokens,
    }
