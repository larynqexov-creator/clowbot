from __future__ import annotations

import json

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.core.outbox_policy import enforce_allowlist
from app.policy.allowlist import load_policy_allowlist
from app.models.tables import OutboxMessage
from app.schemas.outbox_v1 import OutboxPayloadV1, compute_idempotency_key
from app.util.ids import new_uuid
from app.util.time import now_utc

adapter = TypeAdapter(OutboxPayloadV1)


def create_outbox_message(*, db: Session, tenant_id: str, user_id: str | None, payload_dict: dict) -> str:
    """Validate + enforce policy + idempotency insert."""

    # Fill idempotency_key if missing.
    if not payload_dict.get("idempotency_key"):
        payload_dict = dict(payload_dict)
        payload_dict["idempotency_key"] = compute_idempotency_key(payload_dict)

    payload: OutboxPayloadV1 = adapter.validate_python(payload_dict)

    allow_doc = load_policy_allowlist(db, tenant_id=tenant_id)
    decision = enforce_allowlist(payload, tenant_allowlist=allow_doc.allowlist)
    payload = decision.payload

    existing = (
        db.query(OutboxMessage)
        .filter(OutboxMessage.tenant_id == tenant_id, OutboxMessage.idempotency_key == payload.idempotency_key)
        .one_or_none()
    )
    if existing:
        return existing.id

    # store compact + normalized
    payload_json = payload.model_dump(by_alias=True)

    msg = OutboxMessage(
        id=new_uuid(),
        tenant_id=tenant_id,
        user_id=user_id,
        channel=payload.kind,
        to=_to_field(payload),
        subject=_subject_field(payload),
        body=_body_field(payload),
        payload=payload_json,
        idempotency_key=payload.idempotency_key,
        meta={"policy_upgraded_to_red": decision.upgraded_to_red},
        status="QUEUED",
        created_at=now_utc(),
        sent_at=None,
    )
    db.add(msg)
    db.commit()
    return msg.id


def _to_field(payload: OutboxPayloadV1) -> str:
    if payload.kind == "email":
        return ",".join([x.email for x in payload.message.to])
    if payload.kind == "telegram":
        return payload.message.chat.chat_id or payload.message.chat.username or ""
    return payload.message.repo


def _subject_field(payload: OutboxPayloadV1) -> str | None:
    if payload.kind == "email":
        return payload.message.subject
    if payload.kind == "github_issue":
        return payload.message.title
    return None


def _body_field(payload: OutboxPayloadV1) -> str:
    if payload.kind == "email":
        return payload.message.body.text or payload.message.body.markdown or ""
    if payload.kind == "telegram":
        return payload.message.text
    return payload.message.body.markdown
