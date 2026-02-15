from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.tables import AuditLog, Document, InboxItem, Project, ProjectAsset, ProjectDecision, Task
from app.util.ids import new_uuid
from app.util.time import now_utc


@dataclass
class ProjectRef:
    project: Project


def audit(
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


def resolve_project(
    db: Session,
    *,
    tenant_id: str,
    project_id: str | None = None,
    project_slug: str | None = None,
) -> Project | None:
    q = db.query(Project).filter(Project.tenant_id == tenant_id)
    if project_id:
        return q.filter(Project.id == project_id).one_or_none()
    if project_slug:
        return q.filter(Project.slug == project_slug).one_or_none()
    return None


def create_project(db: Session, *, tenant_id: str, slug: str, title: str) -> Project:
    now = now_utc()
    p = Project(id=new_uuid(), tenant_id=tenant_id, slug=slug, title=title, status="ACTIVE", created_at=now)
    db.add(p)
    db.commit()
    return p


def create_inbox_text(
    db: Session,
    *,
    tenant_id: str,
    user_id: str | None,
    project: Project | None,
    title: str | None,
    text: str,
    tags: list[str] | None,
    source: str,
) -> InboxItem:
    now = now_utc()
    item = InboxItem(
        id=new_uuid(),
        tenant_id=tenant_id,
        project_id=project.id if project else None,
        kind="text",
        title=title,
        text=text,
        object_key=None,
        content_type="text/plain; charset=utf-8",
        status="DONE",
        tags=tags or [],
        source=source or "api",
        created_at=now,
    )
    db.add(item)

    # Store text as a searchable document.
    doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="project",
        doc_type="inbox_text",
        title=title or "Inbox text",
        content_text=text,
        object_key=None,
        meta={"project_id": item.project_id, "inbox_item_id": item.id, "tags": tags or [], "source": source},
        created_at=now,
    )
    db.add(doc)

    audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="inbox.ingest",
        severity="INFO",
        message="Inbox text ingested",
        context={"inbox_item_id": item.id, "project_id": item.project_id, "doc_id": doc.id},
    )

    db.commit()

    # Best-effort vector upsert
    try:
        from app.memory.vector_store import upsert_document_text_best_effort

        upsert_document_text_best_effort(
            tenant_id=tenant_id, doc_id=doc.id, domain="project", source_type="inbox_text", text=text
        )
    except Exception:
        pass

    if project:
        refresh_project_library(db, tenant_id=tenant_id, project_id=project.id)

    return item


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_asset_object_key(*, tenant_id: str, project_id: str, asset_id: str, filename: str) -> str:
    return f"{tenant_id}/projects/{project_id}/assets/{asset_id}/{filename}"


def create_inbox_file_records(
    db: Session,
    *,
    tenant_id: str,
    user_id: str | None,
    project: Project | None,
    title: str | None,
    filename: str,
    content_type: str,
    data: bytes,
    tags: list[str] | None,
    source: str,
) -> tuple[InboxItem, ProjectAsset | None, Document]:
    now = now_utc()
    inbox_id = new_uuid()
    asset_id = new_uuid()

    project_id = project.id if project else None
    object_key = build_asset_object_key(
        tenant_id=tenant_id, project_id=project.id if project else "unassigned", asset_id=asset_id, filename=filename
    )

    item = InboxItem(
        id=inbox_id,
        tenant_id=tenant_id,
        project_id=project_id,
        kind="file",
        title=title or filename,
        text=None,
        object_key=object_key,
        content_type=content_type,
        status="QUEUED",
        tags=tags or [],
        source=source or "api",
        created_at=now,
    )
    db.add(item)

    # Only create asset row if project is known at ingest time.
    # If unassigned, the item can be triaged later.
    asset: ProjectAsset | None = None
    if project:
        asset = ProjectAsset(
            id=asset_id,
            tenant_id=tenant_id,
            project_id=project.id,
            inbox_item_id=item.id,
            filename=filename,
            content_type=content_type,
            object_key=object_key,
            sha256=_sha256(data),
            size_bytes=len(data),
            created_at=now,
        )
        db.add(asset)

    asset_meta_doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="project",
        doc_type="asset_meta",
        title=title or filename,
        content_text=None,
        object_key=object_key,
        meta={
            "project_id": project_id,
            "inbox_item_id": item.id,
            "asset_id": asset.id if project else None,
            "filename": filename,
            "content_type": content_type,
            "sha256": _sha256(data),
            "size_bytes": len(data),
            "tags": tags or [],
            "source": source,
        },
        created_at=now,
    )
    db.add(asset_meta_doc)

    audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="inbox.ingest",
        severity="INFO",
        message="Inbox file ingested",
        context={
            "inbox_item_id": item.id,
            "project_id": project_id,
            "asset_id": asset.id if project else None,
            "doc_id": asset_meta_doc.id,
            "object_key": object_key,
        },
    )

    db.commit()
    return item, asset, asset_meta_doc


def refresh_project_library(db: Session, *, tenant_id: str, project_id: str) -> None:
    """Rebuilds project mindmap + library index as Documents.

    The output is intentionally overview-level: counts + top recent items.
    """

    now = now_utc()

    proj: Project | None = (
        db.query(Project).filter(Project.tenant_id == tenant_id, Project.id == project_id).one_or_none()
    )
    if not proj:
        return

    # Recent items
    assets = (
        db.query(ProjectAsset)
        .filter(ProjectAsset.tenant_id == tenant_id, ProjectAsset.project_id == project_id)
        .order_by(ProjectAsset.created_at.desc())
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
    inbox = (
        db.query(InboxItem)
        .filter(InboxItem.tenant_id == tenant_id, InboxItem.project_id == project_id)
        .order_by(InboxItem.created_at.desc())
        .limit(20)
        .all()
    )

    asset_count = (
        db.query(ProjectAsset)
        .filter(ProjectAsset.tenant_id == tenant_id, ProjectAsset.project_id == project_id)
        .count()
    )
    decision_count = (
        db.query(ProjectDecision)
        .filter(ProjectDecision.tenant_id == tenant_id, ProjectDecision.project_id == project_id)
        .count()
    )
    inbox_count = (
        db.query(InboxItem).filter(InboxItem.tenant_id == tenant_id, InboxItem.project_id == project_id).count()
    )

    # Tasks (best-effort): count tasks where metadata.project_id == project_id.
    task_count = 0
    try:
        # sqlite JSON ops can be flaky; keep best-effort.
        task_count = (
            db.query(Task)
            .filter(Task.tenant_id == tenant_id)
            .filter(Task.meta["project_id"].as_string() == project_id)
            .count()
        )
    except Exception:
        task_count = 0

    def short(x: str, n: int = 8) -> str:
        return (x or "")[:n]

    map_index: dict[str, dict] = {}

    lines = [
        "flowchart TD",
        f'  P["{proj.title}\\n({proj.slug})"]:::root',
        f"  P --> A[\"Assets ({asset_count})\"]:::group",
        f"  P --> D[\"Decisions ({decision_count})\"]:::group",
        f"  P --> I[\"Inbox ({inbox_count})\"]:::group",
        f"  P --> T[\"Tasks ({task_count})\"]:::group",
        "",
        # Live links (mermaid click)
        f"  click P \"/projects/{project_id}/library/index\" \"Library index\"",
        f"  click A \"/projects/{project_id}/library\" \"Assets list\"",
        f"  click D \"/projects/{project_id}/library\" \"Decisions list\"",
        f"  click I \"/projects/{project_id}/library\" \"Inbox list\"",
    ]

    # Add top 7 per section
    for a in assets[:7]:
        node = f"AS_{short(a.id)}"
        label = f"{a.filename}\\n({short(a.id)})"
        lines.append(f'  A --> {node}["{_escape_mermaid(label)}"]:::item')
        lines.append(f"  click {node} \"/projects/{project_id}/assets/{a.id}/preview\" \"Preview asset\"")
        map_index[node] = {
            "type": "asset",
            "title": a.filename,
            "asset_id": a.id,
            "api_link": f"/projects/{project_id}/assets/{a.id}/preview",
        }

    for d in decisions[:7]:
        node = f"DC_{short(d.id)}"
        label = f"{d.title}\\n({short(d.id)})"
        lines.append(f'  D --> {node}["{_escape_mermaid(label)}"]:::item')
        lines.append(f"  click {node} \"/projects/{project_id}/decisions/{d.id}\" \"Open decision\"")
        map_index[node] = {
            "type": "decision",
            "title": d.title,
            "decision_id": d.id,
            "api_link": f"/projects/{project_id}/decisions/{d.id}",
        }

    for it in inbox[:7]:
        node = f"IN_{short(it.id)}"
        label = f"{(it.title or it.kind)}\\n({short(it.id)})"
        lines.append(f'  I --> {node}["{_escape_mermaid(label)}"]:::item')
        map_index[node] = {
            "type": "inbox_item",
            "title": it.title,
            "inbox_item_id": it.id,
            "api_link": f"/projects/{project_id}/library",
        }

    lines.extend(
        [
            "  classDef root fill:#dbeafe,stroke:#1d4ed8,color:#000;",
            "  classDef group fill:#e5e7eb,stroke:#6b7280,color:#000;",
            "  classDef item fill:#fff7ed,stroke:#c2410c,color:#000;",
        ]
    )

    mermaid = "\n".join(lines) + "\n"

    mindmap_doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="mindmap",
        doc_type="project_mindmap",
        title=f"Project mindmap: {proj.title}",
        content_text=mermaid,
        object_key=None,
        meta={"project_id": project_id, "project_slug": proj.slug, "map_index": map_index},
        created_at=now,
    )
    db.add(mindmap_doc)

    index_md = build_project_library_index_md(
        project=proj, inbox=inbox, assets=assets, decisions=decisions, asset_count=asset_count, inbox_count=inbox_count
    )
    index_doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="project",
        doc_type="project_library_index",
        title=f"Project library index: {proj.title}",
        content_text=index_md,
        object_key=None,
        meta={"project_id": project_id, "project_slug": proj.slug},
        created_at=now,
    )
    db.add(index_doc)

    db.commit()


def build_project_library_index_md(
    *,
    project: Project,
    inbox: list[InboxItem],
    assets: list[ProjectAsset],
    decisions: list[ProjectDecision],
    asset_count: int,
    inbox_count: int,
) -> str:
    def short(x: str, n: int = 8) -> str:
        return (x or "")[:n]

    lines: list[str] = []
    lines.append(f"# Project library: {project.title}")
    lines.append("")
    lines.append(f"- slug: `{project.slug}`")
    lines.append(f"- project_id: `{project.id}`")
    lines.append("")

    lines.append("## Latest assets")
    lines.append("")
    for a in assets[:20]:
        lines.append(f"- `{short(a.id)}` **{a.filename}** ({a.content_type}, {a.size_bytes} bytes)")
    if not assets:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Latest inbox items")
    lines.append("")
    for it in inbox[:20]:
        lines.append(f"- `{short(it.id)}` **{it.kind}** {it.title or ''} (status={it.status})")
    if not inbox:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Latest decisions")
    lines.append("")
    for d in decisions[:20]:
        lines.append(f"- `{short(d.id)}` **{d.title}**")
    if not decisions:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Links")
    lines.append("")
    lines.append(f"- GET `/projects/{project.id}/library`")
    lines.append(f"- GET `/projects/{project.id}/library/index`")
    lines.append(f"- GET `/mindmap/project/{project.id}`")
    lines.append("")
    return "\n".join(lines) + "\n"


def _escape_mermaid(s: str) -> str:
    return (s or "").replace('"', "'")
