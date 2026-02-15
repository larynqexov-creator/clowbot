from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.tables import Task
from app.skills.registry import SKILLS
from app.util.ids import new_uuid
from app.util.time import now_utc


@dataclass(frozen=True)
class SkillRunResult:
    status: str  # DONE|BLOCKED|FAILED
    reason: str | None
    artifacts: dict
    created_task_ids: list[str]
    outbox_ids: list[str]
    pending_action_ids: list[str]
    confirmation_tokens: dict[str, str]


def _create_task(db: Session, *, tenant_id: str, title: str, status: str = "TODO", meta: dict | None = None) -> str:
    tid = new_uuid()
    db.add(
        Task(
            id=tid,
            tenant_id=tenant_id,
            workflow_id=None,
            title=title,
            status=status,
            meta=meta or {},
            created_at=now_utc(),
        )
    )
    return tid


def run_skill(db: Session, *, tenant_id: str, user_id: str | None, skill_name: str, inputs: dict) -> SkillRunResult:
    fn = SKILLS.get(skill_name)
    if not fn:
        return SkillRunResult(
            status="FAILED",
            reason=f"Unknown skill: {skill_name}",
            artifacts={},
            created_task_ids=[],
            outbox_ids=[],
            pending_action_ids=[],
            confirmation_tokens={},
        )

    return fn(db=db, tenant_id=tenant_id, user_id=user_id, inputs=inputs)
