from __future__ import annotations

from dataclasses import dataclass

from app.schemas.outbox_v1 import Allowlist, OutboxPayloadV1


@dataclass(frozen=True)
class PolicyDecision:
    payload: OutboxPayloadV1
    upgraded_to_red: bool


def _email_allowed(payload: OutboxPayloadV1) -> bool:
    if payload.kind != "email":
        return True
    allow = payload.policy.allowlist
    allowed_domains = {d.lower().lstrip("@") for d in allow.email_domains}
    allowed_emails = {e.lower() for e in allow.emails}

    def ok_addr(addr: str) -> bool:
        a = addr.lower()
        if a in allowed_emails:
            return True
        if "@" in a:
            dom = a.split("@", 1)[1]
            return dom in allowed_domains
        return False

    all_addrs = [x.email for x in payload.message.to + payload.message.cc + payload.message.bcc]
    return all(ok_addr(a) for a in all_addrs)


def _telegram_allowed(payload: OutboxPayloadV1) -> bool:
    if payload.kind != "telegram":
        return True
    allow = set(payload.policy.allowlist.telegram_chats)
    chat = payload.message.chat
    target = chat.chat_id or chat.username
    if not target:
        return False
    return target in allow


def _github_allowed(payload: OutboxPayloadV1) -> bool:
    if payload.kind != "github_issue":
        return True
    allow = set(payload.policy.allowlist.github_repos)
    return payload.message.repo in allow


def enforce_allowlist(payload: OutboxPayloadV1, *, tenant_allowlist: Allowlist | None = None) -> PolicyDecision:
    """If targets are not allowlisted, auto-upgrade to RED + requires_approval.

    tenant_allowlist, if provided, is merged into payload.policy.allowlist (union).
    """

    if tenant_allowlist is not None:
        allow = payload.policy.allowlist
        payload.policy.allowlist = Allowlist(
            email_domains=list(dict.fromkeys((allow.email_domains or []) + (tenant_allowlist.email_domains or []))),
            emails=list(dict.fromkeys((allow.emails or []) + (tenant_allowlist.emails or []))),
            telegram_chats=list(dict.fromkeys((allow.telegram_chats or []) + (tenant_allowlist.telegram_chats or []))),
            github_repos=list(dict.fromkeys((allow.github_repos or []) + (tenant_allowlist.github_repos or []))),
        )

    allowed = _email_allowed(payload) and _telegram_allowed(payload) and _github_allowed(payload)

    upgraded = False
    if not allowed:
        upgraded = True
        payload.policy.risk = "RED"
        payload.policy.requires_approval = True

    # Email rules: if markdown present but no text, we still allow; preview renderer can derive.
    return PolicyDecision(payload=payload, upgraded_to_red=upgraded)
