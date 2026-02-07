from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.tables import Workflow, Task, Document, AuditLog
from app.tasks.grant_tasks import run_grants_workflow_task
from app.util.ids import new_uuid
from app.util.time import now_utc


def start_grants_workflow(*, db: Session, tenant_id: str, user_id: str) -> str:
    wf_id = new_uuid()
    wf = Workflow(
        id=wf_id,
        tenant_id=tenant_id,
        domain="science",
        type="grants",
        status="RUNNING",
        state="NEW",
        artifacts={},
        last_error=None,
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    db.add(wf)
    db.add(
        AuditLog(
            id=new_uuid(),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="WORKFLOW_STARTED",
            severity="INFO",
            message="Science grants workflow created",
            context={"workflow_id": wf_id},
            created_at=now_utc(),
        )
    )
    db.commit()

    run_grants_workflow_task.delay(tenant_id=tenant_id, user_id=user_id, workflow_id=wf_id)
    return wf_id


def run_grants_workflow_steps(*, db: Session, tenant_id: str, user_id: str, workflow_id: str) -> None:
    from app.domain.science.grants.mock_sources import mock_grants

    wf: Workflow | None = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
        .one_or_none()
    )
    if not wf:
        return

    try:
        grants = mock_grants()
        wf.artifacts = {"grants": grants}
        wf.state = "SOURCED"
        wf.updated_at = now_utc()
        db.add(wf)
        db.commit()

        best = grants[0]
        wf.artifacts["selected_grant"] = best
        wf.state = "ANALYZED"
        wf.updated_at = now_utc()
        db.add(wf)
        db.commit()

        doc_id = new_uuid()
        draft = f"Draft for {best['grant_id']}: {best['title']}\nDeadline: {best['deadline']}\n"
        db.add(
            Document(
                id=doc_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                domain="science",
                title=f"Grant draft: {best['title']}",
                content_text=draft,
                object_key=None,
                meta={"grant_id": best["grant_id"], "source": "mock"},
                created_at=now_utc(),
            )
        )
        db.commit()

        wf.artifacts["draft_document_id"] = doc_id
        wf.state = "DRAFTED"
        wf.updated_at = now_utc()
        db.add(wf)
        db.commit()

        task_ids: list[str] = []
        for title in ["Outline proposal", "Draft budget", "Submission checklist"]:
            t = Task(
                id=new_uuid(),
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                title=f"{best['grant_id']}: {title}",
                status="OPEN",
                meta={"type": "work_item"},
                created_at=now_utc(),
            )
            db.add(t)
            task_ids.append(t.id)
        db.commit()

        wf.artifacts["created_task_ids"] = task_ids
        wf.state = "NOTIFIED"
        wf.status = "COMPLETED"
        wf.updated_at = now_utc()
        db.add(wf)
        db.commit()

    except Exception as e:
        wf.state = "FAILED"
        wf.status = "FAILED"
        wf.last_error = str(e)
        wf.updated_at = now_utc()
        db.add(wf)
        db.commit()
        raise
