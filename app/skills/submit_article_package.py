from __future__ import annotations

import hashlib
import secrets

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.models.tables import Document, PendingAction
from app.outbox.service import create_outbox_message
from app.schemas.outbox_v1 import OutboxPayloadV1
from app.skills.registry import register
from app.skills.runner import SkillRunResult, _create_task
from app.util.ids import new_uuid
from app.util.time import now_utc

adapter = TypeAdapter(OutboxPayloadV1)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@register("submit_article_package")
def submit_article_package(*, db: Session, tenant_id: str, user_id: str | None, inputs: dict) -> SkillRunResult:
    manuscript_doc_id = inputs.get("manuscript_doc_id")
    manuscript_object_key = inputs.get("manuscript_object_key")
    editor_email = inputs.get("editor_email")
    journal_name = inputs.get("journal_name") or "(unspecified journal)"

    created_tasks: list[str] = []

    if not manuscript_doc_id and not manuscript_object_key:
        created_tasks.append(_create_task(db, tenant_id=tenant_id, title="[ARTICLE] Provide manuscript_doc_id or manuscript_object_key"))
        if not editor_email:
            created_tasks.append(_create_task(db, tenant_id=tenant_id, title="[ARTICLE] Provide editor_email (target recipient)"))
        db.commit()
        return SkillRunResult(
            status="BLOCKED",
            reason="Missing manuscript input",
            artifacts={},
            created_task_ids=created_tasks,
            outbox_ids=[],
            pending_action_ids=[],
            confirmation_tokens={},
        )

    # Minimal cover letter + checklist.
    cover_md = (
        f"# Cover Letter\n\n"
        f"Journal: {journal_name}\n\n"
        "Dear Editor,\n\n"
        "Please consider our manuscript for publication.\n\n"
        "Sincerely,\nClowBot\n"
    )
    checklist_md = (
        "# Submission checklist\n\n"
        "- [ ] Manuscript attached\n"
        "- [ ] Figures attached (if any)\n"
        "- [ ] Metadata included (title/abstract/keywords)\n"
        "- [ ] Cover letter included\n"
    )

    cover_doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="article",
        doc_type="cover_letter",
        title="Cover letter",
        content_text=cover_md,
        object_key=None,
        meta={},
        created_at=now_utc(),
    )
    checklist_doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="article",
        doc_type="submission_checklist",
        title="Submission checklist",
        content_text=checklist_md,
        object_key=None,
        meta={},
        created_at=now_utc(),
    )
    db.add(cover_doc)
    db.add(checklist_doc)
    db.commit()

    if not editor_email:
        created_tasks.append(_create_task(db, tenant_id=tenant_id, title="[ARTICLE] Provide editor_email to build email outbox item"))
        db.commit()
        return SkillRunResult(
            status="BLOCKED",
            reason="Missing editor_email",
            artifacts={"cover_letter_doc_id": cover_doc.id, "checklist_doc_id": checklist_doc.id},
            created_task_ids=created_tasks,
            outbox_ids=[],
            pending_action_ids=[],
            confirmation_tokens={},
        )

    attachments = []
    if manuscript_object_key:
        attachments.append(
            {
                "id": "att-manuscript",
                "filename": "manuscript",
                "content_type": "application/octet-stream",
                "object_key": manuscript_object_key,
                "disposition": "attachment",
            }
        )

    # Build email outbox payload. Sending should require approval unless allowlist allows.
    payload_dict = {
        "schema": "clowbot.outbox.v1",
        "kind": "email",
        "idempotency_key": "",
        "context": {"source": "skill_runner"},
        "policy": {
            "risk": "RED",
            "requires_approval": True,
            "allowlist": {"email_domains": [], "emails": [editor_email], "telegram_chats": [], "github_repos": []},
        },
        "message": {
            "from": {"name": "ClowBot", "email": "noreply@local"},
            "to": [{"email": editor_email, "name": "Editor"}],
            "cc": [],
            "bcc": [],
            "reply_to": [],
            "subject": f"Submission: manuscript to {journal_name}",
            "body": {"markdown": cover_md, "text": cover_md},
            "headers": {},
        },
        "attachments": attachments,
    }

    outbox_id = create_outbox_message(db=db, tenant_id=tenant_id, user_id=user_id, payload_dict=payload_dict)

    # Create a RED pending action that will approve sending this outbox item.
    token = secrets.token_urlsafe(18)
    pa = PendingAction(
        id=new_uuid(),
        tenant_id=tenant_id,
        user_id=user_id,
        risk_level="RED",
        action_type="outbox.send",
        payload={"outbox_id": outbox_id},
        status="PENDING",
        confirmation_token_hash=_hash_token(token),
        created_at=now_utc(),
        decided_at=None,
    )
    db.add(pa)
    db.commit()

    return SkillRunResult(
        status="DONE",
        reason=None,
        artifacts={"cover_letter_doc_id": cover_doc.id, "checklist_doc_id": checklist_doc.id},
        created_task_ids=created_tasks,
        outbox_ids=[outbox_id],
        pending_action_ids=[pa.id],
        confirmation_tokens={pa.id: token},
    )
