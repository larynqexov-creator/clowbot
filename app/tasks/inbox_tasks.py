from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.celery_app import celery
from app.core.db import SessionLocal
from app.memory.object_store import get_bytes
from app.memory.vector_store import upsert_document_text_best_effort
from app.models.tables import Document, InboxItem
from app.project_library.service import audit, refresh_project_library
from app.util.ids import new_uuid
from app.util.time import now_utc

log = logging.getLogger("app")


@celery.task(name="process_inbox_item")
def process_inbox_item(inbox_item_id: str) -> dict:
    """Process an inbox item (best-effort, no external tokens).

    Idempotency:
    - If item is already DONE, return ok.
    - For PDF extraction, do not create duplicate extracted_text Documents for the same inbox_item.

    Concurrency:
    - On Postgres, uses SELECT .. FOR UPDATE SKIP LOCKED to avoid multiple workers picking the same row.

    Processing rules:
    - PDF: extract text -> Document(doc_type=extracted_text) -> vector upsert
    - Audio/Image: stub (no OCR/transcription)
    """

    with SessionLocal() as db:
        q = db.query(InboxItem).filter(InboxItem.id == inbox_item_id)

        # On Postgres, avoid multiple workers picking the same rows.
        try:
            if db.bind and db.bind.dialect.name == "postgresql":
                q = q.with_for_update(skip_locked=True)
        except Exception:
            pass

        item: InboxItem | None = q.one_or_none()
        if not item:
            return {"ok": False, "reason": "not_found"}

        # Idempotent: already processed
        if item.status == "DONE":
            return {"ok": True, "status": "DONE", "idempotent": True}

        tenant_id = item.tenant_id
        project_id = item.project_id

        # Mark processing (best-effort)
        try:
            item.status = "PROCESSING"
            db.commit()
        except Exception:
            db.rollback()

        try:
            _process(db, item=item)
            item.status = "DONE"
            db.commit()
            audit(
                db,
                tenant_id=tenant_id,
                user_id=None,
                event_type="inbox.process",
                severity="INFO",
                message="Inbox item processed",
                context={"inbox_item_id": inbox_item_id, "project_id": project_id, "status": "DONE"},
            )
            db.commit()
        except Exception as e:
            item.status = "FAILED"
            db.commit()
            audit(
                db,
                tenant_id=tenant_id,
                user_id=None,
                event_type="inbox.process",
                severity="ERROR",
                message="Inbox item processing failed",
                context={"inbox_item_id": inbox_item_id, "error": str(e)},
            )
            db.commit()
            return {"ok": False, "reason": "failed", "error": str(e)}

        if project_id:
            refresh_project_library(db, tenant_id=tenant_id, project_id=project_id)

        return {"ok": True, "status": "DONE"}


def _process(db: Session, *, item: InboxItem) -> None:
    if item.kind != "file":
        return

    ctype = (item.content_type or "").lower()
    key = item.object_key
    if not key:
        return

    # PDF extraction
    if "pdf" in ctype or key.lower().endswith(".pdf"):
        # Idempotency: do not create duplicate extracted_text docs for the same inbox item.
        existing: Document | None = (
            db.query(Document)
            .filter(
                Document.tenant_id == item.tenant_id,
                Document.domain == "project",
                Document.doc_type == "extracted_text",
            )
            .order_by(Document.created_at.desc())
            .limit(50)
            .all()
        )
        for d in existing or []:
            if (d.meta or {}).get("inbox_item_id") == item.id:
                return

        data = get_bytes(object_key=key) or b""
        text = extract_pdf_text(data)
        if text.strip():
            doc = Document(
                id=new_uuid(),
                tenant_id=item.tenant_id,
                workflow_id=None,
                domain="project",
                doc_type="extracted_text",
                title=f"Extracted text: {item.title or 'PDF'}",
                content_text=text,
                object_key=None,
                meta={"project_id": item.project_id, "inbox_item_id": item.id, "source_object_key": key},
                created_at=now_utc(),
            )
            db.add(doc)
            db.commit()
            upsert_document_text_best_effort(
                tenant_id=item.tenant_id, doc_id=doc.id, domain="project", source_type="extracted_text", text=text
            )
        return

    # Other kinds: stub
    return


def extract_pdf_text(data: bytes) -> str:
    """Extract text from a PDF payload. Best-effort.

    Primary extractor: pypdf.
    Fallback: scan for simple literal strings in content streams.

    Note: this fallback is intentionally conservative and exists mainly to make
    ingestion robust in offline environments and unit tests.
    """

    if not data:
        return ""

    text = ""
    try:
        from pypdf import PdfReader

        import io

        reader = PdfReader(io.BytesIO(data))
        parts: list[str] = []
        for p in reader.pages:
            try:
                parts.append(p.extract_text() or "")
            except Exception:
                parts.append("")
        text = "\n".join(parts).strip()
    except Exception:
        text = ""

    if text:
        return text + "\n"

    # Fallback: very naive literal string capture for content like "(Hello) Tj".
    try:
        import re

        raw = data.decode("latin-1", errors="ignore")
        # capture up to 200 chars to avoid runaway
        matches = re.findall(r"\(([^\)\r\n]{1,200})\)\s*Tj", raw)
        if matches:
            return "\n".join(matches).strip() + "\n"
    except Exception:
        pass

    return ""
