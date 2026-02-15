from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tables import Document, InboxItem, Project, ProjectAsset, ProjectDecision
from app.skills.registry import register
from app.skills.runner import SkillRunResult, _create_task
from app.util.ids import new_uuid
from app.util.time import now_utc


@register("project_library_snapshot")
def project_library_snapshot(*, db: Session, tenant_id: str, user_id: str | None, inputs: dict) -> SkillRunResult:
    """Create a weekly snapshot/summary for a project.

    MVP behavior:
    - Require project_id
    - Save a Document(domain='project', doc_type='project_weekly_snapshot')
    """

    project_id = (inputs or {}).get("project_id")
    if not project_id:
        tid = _create_task(db, tenant_id=tenant_id, title="[PROJECT SNAPSHOT] Provide project_id")
        db.commit()
        return SkillRunResult(
            status="BLOCKED",
            reason="Missing project_id",
            artifacts={},
            created_task_ids=[tid],
            outbox_ids=[],
            pending_action_ids=[],
            confirmation_tokens={},
        )

    proj: Project | None = (
        db.query(Project).filter(Project.tenant_id == tenant_id, Project.id == project_id).one_or_none()
    )
    if not proj:
        return SkillRunResult(
            status="FAILED",
            reason="Project not found",
            artifacts={"project_id": project_id},
            created_task_ids=[],
            outbox_ids=[],
            pending_action_ids=[],
            confirmation_tokens={},
        )

    assets = (
        db.query(ProjectAsset)
        .filter(ProjectAsset.tenant_id == tenant_id, ProjectAsset.project_id == project_id)
        .order_by(ProjectAsset.created_at.desc())
        .limit(20)
        .all()
    )
    inbox = (
        db.query(InboxItem)
        .filter(InboxItem.tenant_id == tenant_id, InboxItem.project_id == project_id)
        .order_by(InboxItem.created_at.desc())
        .limit(20)
        .all()
    )
    decisions = (
        db.query(ProjectDecision)
        .filter(ProjectDecision.tenant_id == tenant_id, ProjectDecision.project_id == project_id)
        .order_by(ProjectDecision.created_at.desc())
        .limit(20)
        .all()
    )

    lines: list[str] = []
    lines.append(f"# Project weekly snapshot: {proj.title}")
    lines.append("")
    lines.append(f"- project_id: `{proj.id}`")
    lines.append(f"- slug: `{proj.slug}`")
    lines.append("")

    lines.append("## New / latest assets")
    lines.append("")
    for a in assets:
        lines.append(f"- `{a.id[:8]}` {a.filename} ({a.content_type}, {a.size_bytes} bytes)")
    if not assets:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Latest inbox items")
    lines.append("")
    for it in inbox:
        lines.append(f"- `{it.id[:8]}` {it.kind} {it.title or ''} (status={it.status})")
    if not inbox:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Latest decisions")
    lines.append("")
    for d in decisions:
        lines.append(f"- `{d.id[:8]}` {d.title}")
    if not decisions:
        lines.append("- (none)")
    lines.append("")

    md = "\n".join(lines) + "\n"

    doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="project",
        doc_type="project_weekly_snapshot",
        title=f"Weekly snapshot: {proj.title}",
        content_text=md,
        object_key=None,
        meta={"project_id": proj.id, "project_slug": proj.slug, "created_by": user_id},
        created_at=now_utc(),
    )
    db.add(doc)
    db.commit()

    return SkillRunResult(
        status="DONE",
        reason=None,
        artifacts={"snapshot_doc_id": doc.id, "project_id": proj.id},
        created_task_ids=[],
        outbox_ids=[],
        pending_action_ids=[],
        confirmation_tokens={},
    )
