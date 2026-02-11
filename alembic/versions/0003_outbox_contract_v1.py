"""outbox contract v1 (payload + idempotency)

Revision ID: 0003_outbox_contract_v1
Revises: 0002_jarvis_layer
Create Date: 2026-02-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_outbox_contract_v1"
down_revision = "0002_jarvis_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outbox_messages", sa.Column("payload", sa.JSON(), nullable=True))
    op.add_column("outbox_messages", sa.Column("idempotency_key", sa.String(length=120), nullable=True))
    op.create_index(
        "ux_outbox_messages_tenant_idempotency",
        "outbox_messages",
        ["tenant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_outbox_messages_tenant_idempotency", table_name="outbox_messages")
    op.drop_column("outbox_messages", "idempotency_key")
    op.drop_column("outbox_messages", "payload")
