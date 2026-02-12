from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.memory.vector_store import upsert_document_text_best_effort
from app.models.tables import AuditLog, Document
from app.util.ids import new_uuid
from app.util.time import now_utc


@dataclass(frozen=True)
class BootstrapSource:
    source_path: str
    doc_type: str
    title: str


SOT_SOURCES: list[BootstrapSource] = [
    BootstrapSource(source_path="CLOWDBOT_SUPERMISSION.md", doc_type="mission", title="mission"),
    BootstrapSource(source_path="STATUS.md", doc_type="status", title="status"),
    BootstrapSource(source_path="NEXT.md", doc_type="next", title="next"),
    BootstrapSource(source_path="BACKLOG.md", doc_type="backlog", title="backlog"),
    BootstrapSource(source_path="MINDMAP.md", doc_type="mindmap_dev", title="mindmap_dev"),
    BootstrapSource(source_path="BOOTSTRAP.md", doc_type="bootstrap", title="bootstrap"),
]

REQUIRED_DOC_TYPES = {"mission", "status", "next"}


def _repo_root() -> Path:
    # app/memory/bootstrap.py -> app/memory -> app -> repo
    here = Path(__file__).resolve()
    root = (here.parents[2] / settings.SOT_ROOT_DIR).resolve()
    return root


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_context_version(doc_sha_by_type: dict[str, str]) -> str:
    # Stable order
    parts = []
    for k in sorted(doc_sha_by_type.keys()):
        parts.append(f"{k}:{doc_sha_by_type[k]}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _audit(db: Session, *, tenant_id: str, user_id: str | None, event_type: str, severity: str, message: str, context: dict) -> None:
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


def refresh_bootstrap(
    db: Session,
    *,
    tenant_id: str,
    user_id: str | None,
    root_dir: Path | None = None,
) -> dict[str, Any]:
    root = root_dir or _repo_root()
    refreshed_at = now_utc()

    updated: list[dict[str, Any]] = []
    sha_by_type: dict[str, str] = {}

    for src in SOT_SOURCES:
        p = (root / src.source_path).resolve()
        if not p.exists():
            # create an empty doc version (fail closed later if required)
            content = ""
        else:
            content = p.read_text(encoding="utf-8")

        content_sha = _sha256_text(content)
        sha_by_type[src.doc_type] = content_sha

        # If latest doc matches sha, keep it.
        latest: Document | None = (
            db.query(Document)
            .filter(Document.tenant_id == tenant_id, Document.domain == "sot", Document.doc_type == src.doc_type)
            .order_by(Document.created_at.desc())
            .first()
        )

        latest_sha = None
        if latest:
            latest_sha = (latest.meta or {}).get("content_sha256")

        if latest and latest_sha == content_sha:
            # Still refresh timestamp? we keep immutable docs; status endpoint will compute from max refreshed_at.
            updated.append({"doc_type": src.doc_type, "document_id": latest.id, "updated": False})
            continue

        meta = {
            "source_path": src.source_path,
            "content_sha256": content_sha,
            "refreshed_at": refreshed_at.isoformat(),
            # git_commit optional (left blank; can be filled by a future Git integration)
        }

        doc = Document(
            id=new_uuid(),
            tenant_id=tenant_id,
            workflow_id=None,
            domain="sot",
            doc_type=src.doc_type,
            title=src.title,
            content_text=content,
            object_key=None,
            meta=meta,
            created_at=refreshed_at,
        )
        db.add(doc)
        db.commit()

        # Vector upsert best-effort
        upsert_document_text_best_effort(tenant_id=tenant_id, doc_id=doc.id, domain="sot", source_type=src.doc_type, text=content)

        updated.append({"doc_type": src.doc_type, "document_id": doc.id, "updated": True})

    context_version = compute_context_version(sha_by_type)

    _audit(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type="BOOTSTRAP_REFRESHED",
        severity="INFO",
        message="bootstrap_refreshed",
        context={"context_version": context_version, "updated": updated},
    )
    db.commit()

    return {"ok": True, "updated": updated, "context_version": context_version, "refreshed_at": refreshed_at.isoformat()}


def bootstrap_status(db: Session, *, tenant_id: str) -> dict[str, Any]:
    latest_docs: dict[str, Document] = {}
    sha_by_type: dict[str, str] = {}
    refreshed_at_max = None

    for src in SOT_SOURCES:
        d: Document | None = (
            db.query(Document)
            .filter(Document.tenant_id == tenant_id, Document.domain == "sot", Document.doc_type == src.doc_type)
            .order_by(Document.created_at.desc())
            .first()
        )
        if not d:
            continue
        latest_docs[src.doc_type] = d
        sha = (d.meta or {}).get("content_sha256")
        if sha:
            sha_by_type[src.doc_type] = sha
        ra = (d.meta or {}).get("refreshed_at")
        try:
            # if missing, use created_at
            pass
        finally:
            if refreshed_at_max is None or d.created_at > refreshed_at_max:
                refreshed_at_max = d.created_at

    context_version = compute_context_version(sha_by_type) if sha_by_type else None

    sources = []
    for src in SOT_SOURCES:
        d = latest_docs.get(src.doc_type)
        sources.append(
            {
                "doc_type": src.doc_type,
                "source_path": src.source_path,
                "document_id": d.id if d else None,
                "content_sha256": (d.meta or {}).get("content_sha256") if d else None,
                "created_at": d.created_at.isoformat() if d else None,
            }
        )

    return {
        "tenant_id": tenant_id,
        "refreshed_at": refreshed_at_max.isoformat() if refreshed_at_max else None,
        "context_version": context_version,
        "sources": sources,
    }


def check_bootstrap_fresh(db: Session, *, tenant_id: str) -> tuple[bool, str | None, str]:
    """Return (ok, context_version, reason)."""

    st = bootstrap_status(db, tenant_id=tenant_id)
    now = now_utc()

    # Required docs
    present = {s["doc_type"] for s in st["sources"] if s.get("document_id")}
    missing = sorted(list(REQUIRED_DOC_TYPES - present))
    if missing:
        return False, st.get("context_version"), f"missing_required_documents:{','.join(missing)}"

    refreshed_at = st.get("refreshed_at")
    if not refreshed_at:
        return False, st.get("context_version"), "no_refreshed_at"

    # parse with fromisoformat
    try:
        from datetime import datetime, timezone

        ra = datetime.fromisoformat(refreshed_at.replace("Z", "+00:00"))
        if ra.tzinfo is None:
            # SQLite or legacy rows may be naive; treat as UTC.
            ra = ra.replace(tzinfo=timezone.utc)
    except Exception:
        return False, st.get("context_version"), "bad_refreshed_at"

    max_age = timedelta(hours=int(settings.BOOTSTRAP_MAX_AGE_HOURS))
    if now - ra > max_age:
        return False, st.get("context_version"), "bootstrap_stale"

    return True, st.get("context_version"), "ok"
