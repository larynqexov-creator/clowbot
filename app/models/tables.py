from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

# Use JSONB on Postgres, fallback to JSON for SQLite/test environments.
JSONType = JSON().with_variant(JSONB, "postgresql")

from app.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    api_key_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    artifacts: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    meta: Mapped[dict] = mapped_column("metadata", JSONType, nullable=False, default=dict)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    workflow_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(100), nullable=False, default="generic")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_key: Mapped[str | None] = mapped_column(String(800), nullable=True)
    meta: Mapped[dict] = mapped_column("metadata", JSONType, nullable=False, default=dict)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class PendingAction(Base):
    __tablename__ = "pending_actions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)  # GREEN/YELLOW/RED
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(20), nullable=False)  # PENDING/APPROVED/REJECTED/DONE/FAILED
    confirmation_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # email/telegram/... (logical)
    to: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Canonical contract payload (validated JSON)
    payload: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)

    meta: Mapped[dict] = mapped_column("metadata", JSONType, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(20), nullable=False)  # QUEUED/SENDING/STUB_SENT/SENT/FAILED
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_projects_tenant_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class InboxItem(Base):
    __tablename__ = "inbox_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True)

    kind: Mapped[str] = mapped_column(String(50), nullable=False)  # text/file
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)

    object_key: Mapped[str | None] = mapped_column(String(800), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(200), nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED")
    tags: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="api")

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectAsset(Base):
    __tablename__ = "project_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    inbox_item_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("inbox_items.id"), nullable=True)

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(200), nullable=False)
    object_key: Mapped[str] = mapped_column(String(800), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectDecision(Base):
    __tablename__ = "project_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    links: Mapped[list[dict]] = mapped_column(JSONType, nullable=False, default=list)  # {type,id,title,api_link}
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    context: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
