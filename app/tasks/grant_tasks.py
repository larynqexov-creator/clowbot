from __future__ import annotations

from app.core.celery_app import celery
from app.core.db import SessionLocal


@celery.task(name="app.tasks.grant_tasks.run_grants_workflow_task")
def run_grants_workflow_task(*, tenant_id: str, user_id: str, workflow_id: str) -> dict:
    # Avoid circular imports: import workflow runner inside task.
    from app.domain.science.grants.workflow import run_grants_workflow_steps

    db = SessionLocal()
    try:
        run_grants_workflow_steps(db=db, tenant_id=tenant_id, user_id=user_id, workflow_id=workflow_id)
        return {"ok": True, "workflow_id": workflow_id}
    finally:
        db.close()
