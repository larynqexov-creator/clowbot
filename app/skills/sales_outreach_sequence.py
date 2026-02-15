from __future__ import annotations

import hashlib
import secrets

from sqlalchemy.orm import Session

from app.models.tables import Document, PendingAction
from app.outbox.service import create_outbox_message
from app.skills.registry import register
from app.skills.runner import SkillRunResult, _create_task
from app.util.ids import new_uuid
from app.util.time import now_utc


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@register("sales_outreach_sequence")
def sales_outreach_sequence(*, db: Session, tenant_id: str, user_id: str | None, inputs: dict) -> SkillRunResult:
    """Generate a simple outreach sequence and queue Telegram outbox messages.

    MVP behavior (Telegram):
    - Produces OFFER.md / ICP.md / OUTREACH_MESSAGES.md as Documents.
    - If required inputs are missing, creates tasks and returns BLOCKED.
    - Queues N telegram outbox messages to a single target chat.
    - If policy requires approval, creates a RED pending action for each outbox item.

    Inputs (minimal):
    - chat_id or chat_username (target)
    - product (string)
    - audience (string)
    - leads (optional list[dict] or csv_text)
    - count (optional int, default 5)
    """

    product = (inputs or {}).get("product") or (inputs or {}).get("product_description")
    audience = (inputs or {}).get("audience") or (inputs or {}).get("target_audience")
    chat_id = (inputs or {}).get("chat_id")
    chat_username = (inputs or {}).get("chat_username")
    count = int((inputs or {}).get("count") or 5)

    created_tasks: list[str] = []

    if not product:
        created_tasks.append(_create_task(db, tenant_id=tenant_id, title="[SALES] Provide product (description)"))
    if not audience:
        created_tasks.append(_create_task(db, tenant_id=tenant_id, title="[SALES] Provide audience (ICP constraints)"))
    if not (chat_id or chat_username):
        created_tasks.append(
            _create_task(db, tenant_id=tenant_id, title="[SALES] Provide target Telegram chat_id or chat_username")
        )

    if created_tasks:
        db.commit()
        return SkillRunResult(
            status="BLOCKED",
            reason="Missing required inputs",
            artifacts={},
            created_task_ids=created_tasks,
            outbox_ids=[],
            pending_action_ids=[],
            confirmation_tokens={},
        )

    # Artifacts
    offer_md = (
        "# Offer (draft)\n\n"
        f"Product: {product}\n\n"
        "## Options\n"
        "1) Quick win: audit + shortlist\n"
        "2) Standard: done-for-you setup\n"
        "3) Premium: setup + optimization + reporting\n"
    )
    icp_md = (
        "# ICP (draft)\n\n"
        f"Audience: {audience}\n\n"
        "## Pain\n- time\n- lack of pipeline\n- low conversion\n\n"
        "## Triggers\n- hiring\n- new product\n- funding\n"
    )

    messages = [
        "Привет! Коротко: могу помочь с лидогенерацией/воронкой. Есть 2 вопроса по вашей ситуации?",
        "Если актуально: могу за 30 минут разобрать текущий процесс и дать список быстрых улучшений.",
        "Могу прислать 3 варианта оффера под вашу аудиторию — скажите, кто ваш клиент и средний чек?",
        "Если удобнее — напишите, где сейчас теряются заявки (трафик/конверсия/дожим/повторные продажи).",
        "Ок, не отвлекаю. Если вернётесь к теме — просто ответьте 'да', продолжим.",
    ]
    messages = messages[: max(1, min(count, len(messages)))]

    offer_doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="sales",
        doc_type="offer",
        title="Offer (draft)",
        content_text=offer_md,
        object_key=None,
        meta={},
        created_at=now_utc(),
    )
    icp_doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="sales",
        doc_type="icp",
        title="ICP (draft)",
        content_text=icp_md,
        object_key=None,
        meta={},
        created_at=now_utc(),
    )
    out_md = "# Outreach messages\n\n" + "\n\n".join([f"{i + 1}. {m}" for i, m in enumerate(messages)]) + "\n"
    out_doc = Document(
        id=new_uuid(),
        tenant_id=tenant_id,
        workflow_id=None,
        domain="sales",
        doc_type="outreach_messages",
        title="Outreach messages",
        content_text=out_md,
        object_key=None,
        meta={"chat_id": chat_id, "chat_username": chat_username},
        created_at=now_utc(),
    )

    db.add(offer_doc)
    db.add(icp_doc)
    db.add(out_doc)
    db.commit()

    outbox_ids: list[str] = []
    pending_action_ids: list[str] = []
    confirmation_tokens: dict[str, str] = {}

    for idx, text in enumerate(messages):
        payload_dict = {
            "schema": "clowbot.outbox.v1",
            "kind": "telegram",
            "idempotency_key": "",
            "context": {"source": "skill.sales_outreach_sequence", "sequence_index": idx},
            "policy": {
                "risk": "YELLOW",
                "requires_approval": False,
                # Per-message allowlist can be empty; tenant policy_allowlist can allow it.
                "allowlist": {"email_domains": [], "emails": [], "telegram_chats": [], "github_repos": []},
            },
            "message": {
                "chat": {"chat_id": chat_id, "username": chat_username},
                "parse_mode": "Markdown",
                "text": text,
                "disable_web_page_preview": True,
                "reply_to_message_id": None,
                "silent": False,
            },
            "attachments": [],
        }

        outbox_id = create_outbox_message(db=db, tenant_id=tenant_id, user_id=user_id, payload_dict=payload_dict)
        outbox_ids.append(outbox_id)

        # If allowlist enforcement upgraded this message to require approval, create pending action.
        from app.models.tables import OutboxMessage

        m = db.query(OutboxMessage).filter(OutboxMessage.id == outbox_id).one()
        if (m.payload or {}).get("policy", {}).get("requires_approval"):
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
            pending_action_ids.append(pa.id)
            confirmation_tokens[pa.id] = token

    return SkillRunResult(
        status="DONE",
        reason=None,
        artifacts={"offer_doc_id": offer_doc.id, "icp_doc_id": icp_doc.id, "outreach_messages_doc_id": out_doc.id},
        created_task_ids=[],
        outbox_ids=outbox_ids,
        pending_action_ids=pending_action_ids,
        confirmation_tokens=confirmation_tokens,
    )
