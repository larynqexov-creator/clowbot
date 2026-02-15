from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.schemas.outbox_v1 import OutboxPayloadV1


@dataclass(frozen=True)
class PreviewPack:
    preview_md: str
    preview_payload_json: str
    channel_raw_name: str
    channel_raw: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _email_eml(payload: OutboxPayloadV1) -> str:
    msg = payload.message
    from_line = "ClowBot <noreply@local>"
    if msg.from_:
        from_line = f"{msg.from_.name or 'ClowBot'} <{msg.from_.email}>"

    to_line = ", ".join([f"{x.name or ''} <{x.email}>".strip() for x in msg.to])
    subject = msg.subject

    body_text = msg.body.text
    if not body_text and msg.body.markdown:
        # naive markdown strip
        body_text = msg.body.markdown

    body_text = body_text or ""

    eml = (
        f"From: {from_line}\n"
        f"To: {to_line}\n"
        f"Subject: {subject}\n"
        f"Date: {_now_iso()}\n"
        f"Message-ID: <clowbot-{payload.idempotency_key}@local>\n"
        f"MIME-Version: 1.0\n"
        f'Content-Type: text/plain; charset="utf-8"\n'
        f"\n"
        f"{body_text}\n"
    )

    if payload.attachments:
        eml += "\n[Attachments]\n"
        for a in payload.attachments:
            eml += f"- {a.filename} ({a.content_type}) object_key={a.object_key}\n"

    return eml


def _telegram_preview_json(payload: OutboxPayloadV1) -> str:
    msg = payload.message
    target = msg.chat.chat_id or msg.chat.username
    params = {
        "chat_id": target,
        "text": msg.text,
        "parse_mode": None if msg.parse_mode == "Plain" else msg.parse_mode,
        "disable_web_page_preview": msg.disable_web_page_preview,
    }
    return json.dumps(
        {"adapter_kind": "telegram", "method": "sendMessage", "params": params}, ensure_ascii=False, indent=2
    )


def _github_issue_preview_json(payload: OutboxPayloadV1) -> str:
    msg = payload.message
    obj = {
        "adapter_kind": "github_issue",
        "operation": "create_issue",
        "repo": msg.repo,
        "title": msg.title,
        "body_markdown": msg.body.markdown,
        "labels": msg.labels,
        "assignees": msg.assignees,
        "milestone": msg.milestone,
    }
    return json.dumps(obj, ensure_ascii=False, indent=2)


def render_preview_pack(*, outbox_id: str, payload: OutboxPayloadV1, status: str) -> PreviewPack:
    payload_json = json.dumps(payload.model_dump(by_alias=True), ensure_ascii=False, indent=2)

    targets_summary: dict = {}
    if payload.kind == "email":
        targets_summary["to"] = [x.email for x in payload.message.to]
    elif payload.kind == "telegram":
        targets_summary["telegram"] = payload.message.chat.chat_id or payload.message.chat.username
    else:
        targets_summary["repo"] = payload.message.repo

    front = {
        "outbox_id": outbox_id,
        "schema": payload.schema_,
        "kind": payload.kind,
        "status": status,
        "risk": payload.policy.risk,
        "requires_approval": payload.policy.requires_approval,
        "idempotency_key": payload.idempotency_key,
        "context": payload.context.model_dump(),
        "targets_summary": targets_summary,
        "created_at": _now_iso(),
    }

    fm = "---\n" + "\n".join([f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in front.items()]) + "\n---\n"

    body_md = ""
    if payload.kind == "email":
        body_md = payload.message.body.markdown or payload.message.body.text or ""
    elif payload.kind == "telegram":
        body_md = payload.message.text
    else:
        body_md = payload.message.body.markdown

    preview_md = fm + f"# Outbox Preview — {payload.kind.upper()}\n\n" + "## Body\n\n" + "```\n" + body_md + "\n```\n\n"

    if payload.attachments:
        preview_md += (
            "## Attachments\n"
            + "\n".join([f"- {a.filename} ({a.content_type}) — {a.object_key}" for a in payload.attachments])
            + "\n"
        )

    if payload.kind == "email":
        raw = _email_eml(payload)
        raw_name = "preview.eml"
    elif payload.kind == "telegram":
        raw = _telegram_preview_json(payload)
        raw_name = "preview.json"
    else:
        raw = _github_issue_preview_json(payload)
        raw_name = "preview.json"

    return PreviewPack(
        preview_md=preview_md,
        preview_payload_json=payload_json,
        channel_raw_name=raw_name,
        channel_raw=raw,
    )
