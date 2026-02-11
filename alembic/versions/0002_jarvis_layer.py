"""jarvis layer (doc_type + approvals + outbox)

Revision ID: 0002_jarvis_layer
Revises: 0001_init
Create Date: 2026-02-11
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_jarvis_layer"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("doc_type", sa.String(length=100), nullable=False, server_default="generic"))
    op.create_index("ix_documents_tenant_doctype", "documents", ["tenant_id", "domain", "doc_type"])

    op.create_table(
        "pending_actions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("risk_level", sa.String(length=10), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("confirmation_token_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_pending_actions_tenant_status", "pending_actions", ["tenant_id", "status"])

    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("to", sa.String(length=500), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_messages_tenant_status", "outbox_messages", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_outbox_messages_tenant_status", table_name="outbox_messages")
    op.drop_table("outbox_messages")

    op.drop_index("ix_pending_actions_tenant_status", table_name="pending_actions")
    op.drop_table("pending_actions")

    op.drop_index("ix_documents_tenant_doctype", table_name="documents")
    op.drop_column("documents", "doc_type")
