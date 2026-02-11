from __future__ import annotations

import hashlib
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AttachmentRef(BaseModel):
    id: str
    filename: str
    content_type: str
    object_key: str
    size_bytes: int | None = None
    sha256: str | None = None
    disposition: Literal["attachment", "inline"] = "attachment"
    content_id: str | None = None


class OutboxContext(BaseModel):
    project_id: str | None = None
    task_id: str | None = None
    workflow_id: str | None = None
    source: str | None = None
    trace_id: str | None = None


class Allowlist(BaseModel):
    email_domains: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    telegram_chats: list[str] = Field(default_factory=list)
    github_repos: list[str] = Field(default_factory=list)


class Policy(BaseModel):
    risk: Literal["GREEN", "YELLOW", "RED"] = "YELLOW"
    requires_approval: bool = False
    allowlist: Allowlist = Field(default_factory=Allowlist)


class EmailAddress(BaseModel):
    email: str
    name: str | None = None


class EmailBody(BaseModel):
    markdown: str | None = None
    text: str | None = None
    html: str | None = None


class EmailMessage(BaseModel):
    from_: EmailAddress | None = Field(default=None, alias="from")
    to: list[EmailAddress]
    cc: list[EmailAddress] = Field(default_factory=list)
    bcc: list[EmailAddress] = Field(default_factory=list)
    reply_to: list[EmailAddress] = Field(default_factory=list)
    subject: str
    body: EmailBody
    headers: dict[str, str] = Field(default_factory=dict)


class TelegramChat(BaseModel):
    chat_id: str | None = None
    username: str | None = None


class TelegramMessage(BaseModel):
    chat: TelegramChat
    parse_mode: Literal["Markdown", "MarkdownV2", "HTML", "Plain"] = "Markdown"
    text: str
    disable_web_page_preview: bool = True
    reply_to_message_id: int | None = None
    silent: bool = False


class GitHubIssueBody(BaseModel):
    markdown: str
    text: str | None = None


class GitHubIssueMessage(BaseModel):
    repo: str
    title: str
    body: GitHubIssueBody
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    milestone: str | None = None


class OutboxPayloadBase(BaseModel):
    schema_: Literal["clowbot.outbox.v1"] = Field(default="clowbot.outbox.v1", alias="schema")
    kind: Literal["email", "telegram", "github_issue"]
    idempotency_key: str
    context: OutboxContext = Field(default_factory=OutboxContext)
    policy: Policy = Field(default_factory=Policy)
    attachments: list[AttachmentRef] = Field(default_factory=list)


class OutboxPayloadEmail(OutboxPayloadBase):
    kind: Literal["email"] = "email"
    message: EmailMessage


class OutboxPayloadTelegram(OutboxPayloadBase):
    kind: Literal["telegram"] = "telegram"
    message: TelegramMessage


class OutboxPayloadGitHubIssue(OutboxPayloadBase):
    kind: Literal["github_issue"] = "github_issue"
    message: GitHubIssueMessage


OutboxPayloadV1 = Annotated[
    OutboxPayloadEmail | OutboxPayloadTelegram | OutboxPayloadGitHubIssue,
    Field(discriminator="kind"),
]


def compute_idempotency_key(payload_dict: dict) -> str:
    """Deterministic idempotency key.

    NOTE: This is a conservative v1 implementation: stable JSON hashing.
    """
    import json

    normalized = json.dumps(payload_dict, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{h}"
