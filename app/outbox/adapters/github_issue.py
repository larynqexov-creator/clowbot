from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.models.tables import OutboxMessage
from app.outbox.adapters.base import SendResult
from app.schemas.outbox_v1 import OutboxPayloadV1


def _truncate(s: str, n: int = 200) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n] + "…"


@dataclass(frozen=True)
class GitHubIssueAdapter:
    kind: str = "github_issue"

    def send(self, *, payload: OutboxPayloadV1, outbox_row: OutboxMessage) -> SendResult:
        # Idempotency: if already has external info, do not re-send.
        meta = dict(outbox_row.meta or {})
        ext = (meta.get("external") or {}) if isinstance(meta.get("external"), dict) else {}
        if ext.get("url") or ext.get("id"):
            return SendResult(status="SENT", external_id=ext.get("id"), external_url=ext.get("url"), retryable=False)

        if payload.kind != "github_issue":
            return SendResult(status="FAILED", retryable=False, reason="wrong_payload_kind")

        if not settings.OUTBOX_REAL_SEND_ENABLED:
            return SendResult(status="DRY_RUN_SENT", retryable=False, reason="OUTBOX_REAL_SEND_ENABLED=false")

        token = settings.GITHUB_TOKEN
        if not token:
            return SendResult(status="DRY_RUN_SENT", retryable=False, reason="missing GITHUB_TOKEN")

        repo = payload.message.repo
        title = payload.message.title

        body_md = payload.message.body.markdown

        if payload.attachments:
            body_md += "\n\n---\n## Attachments\n" + "\n".join([f"- {a.filename} ({a.object_key})" for a in payload.attachments])

        url = f"{settings.GITHUB_API_BASE.rstrip('/')}/repos/{repo}/issues"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "clowbot",
        }
        data = {
            "title": title,
            "body": body_md,
            "labels": payload.message.labels or [],
            "assignees": payload.message.assignees or [],
        }

        try:
            resp = httpx.post(url, headers=headers, json=data, timeout=10.0)
            if resp.status_code >= 400:
                return SendResult(
                    status="FAILED",
                    retryable=resp.status_code >= 500,
                    reason=f"github_http_{resp.status_code}:{_truncate(resp.text, 200)}",
                    raw_response={"status_code": resp.status_code, "text": _truncate(resp.text, 1000)},
                )

            j = resp.json()
            external_id = str(j.get("number") or j.get("id") or "") or None
            external_url = j.get("html_url")

            # Don't store entire body; store minimal.
            raw = {
                "number": j.get("number"),
                "id": j.get("id"),
                "html_url": j.get("html_url"),
                "url": j.get("url"),
                "title": j.get("title"),
            }

            return SendResult(status="SENT", external_id=external_id, external_url=external_url, raw_response=raw, retryable=False)
        except Exception as e:
            return SendResult(status="FAILED", retryable=True, reason=f"exception:{type(e).__name__}:{str(e)}")
