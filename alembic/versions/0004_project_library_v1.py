"""project library v1 (projects + inbox + assets + decisions)

Revision ID: 0004_project_library_v1
Revises: 0003_outbox_contract_v1
Create Date: 2026-02-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_project_library_v1"
down_revision = "0003_outbox_contract_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_projects_tenant_slug"),
    )

    op.create_table(
        "inbox_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("object_key", sa.String(length=800), nullable=True),
        sa.Column("content_type", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="QUEUED"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("source", sa.String(length=100), nullable=False, server_default="api"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inbox_items_tenant_created_at", "inbox_items", ["tenant_id", "created_at"], unique=False)
    op.create_index(
        "ix_inbox_items_tenant_project_created_at",
        "inbox_items",
        ["tenant_id", "project_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "project_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("inbox_item_id", sa.String(length=36), sa.ForeignKey("inbox_items.id"), nullable=True),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=200), nullable=False),
        sa.Column("object_key", sa.String(length=800), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_project_assets_tenant_project_created_at",
        "project_assets",
        ["tenant_id", "project_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ux_project_assets_tenant_object_key",
        "project_assets",
        ["tenant_id", "object_key"],
        unique=True,
    )

    op.create_table(
        "project_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("links", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_project_decisions_tenant_project_created_at",
        "project_decisions",
        ["tenant_id", "project_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_decisions_tenant_project_created_at", table_name="project_decisions")
    op.drop_table("project_decisions")

    op.drop_index("ux_project_assets_tenant_object_key", table_name="project_assets")
    op.drop_index("ix_project_assets_tenant_project_created_at", table_name="project_assets")
    op.drop_table("project_assets")

    op.drop_index("ix_inbox_items_tenant_project_created_at", table_name="inbox_items")
    op.drop_index("ix_inbox_items_tenant_created_at", table_name="inbox_items")
    op.drop_table("inbox_items")

    op.drop_table("projects")
