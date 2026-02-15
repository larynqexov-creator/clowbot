from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tables import InboxItem
from app.skills.registry import register
from app.skills.runner import SkillRunResult, _create_task


@register("inbox_triage_weekly")
def inbox_triage_weekly(*, db: Session, tenant_id: str, user_id: str | None, inputs: dict) -> SkillRunResult:
    """Weekly triage of unassigned inbox items.

    MVP behavior:
    - List unassigned inbox items
    - Create TODO tasks prompting assignment

    Later: LLM-assisted routing + decision extraction.
    """

    limit = int((inputs or {}).get("limit") or 50)

    items = (
        db.query(InboxItem)
        .filter(InboxItem.tenant_id == tenant_id, InboxItem.project_id.is_(None))
        .order_by(InboxItem.created_at.desc())
        .limit(limit)
        .all()
    )

    created: list[str] = []
    for it in items:
        created.append(
            _create_task(
                db,
                tenant_id=tenant_id,
                title=f"[INBOX TRIAGE] Assign inbox item {it.id[:8]} ({it.kind}) {it.title or ''}",
                meta={"inbox_item_id": it.id, "kind": it.kind, "source": it.source, "tags": it.tags},
            )
        )

    return SkillRunResult(
        status="DONE",
        reason=None,
        artifacts={"unassigned_count": len(items), "items": [{"id": it.id, "title": it.title, "kind": it.kind} for it in items]},
        created_task_ids=created,
        outbox_ids=[],
        pending_action_ids=[],
        confirmation_tokens={},
    )
