"""add_performance_indexes

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-03-18 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Asset queries: filter by tenant + status (most common query pattern)
    op.create_index(
        "ix_media_assets_tenant_status",
        "media_assets",
        ["tenant_id", "status"],
    )
    # Asset queries: order by created_at descending (default sort)
    op.create_index(
        "ix_media_assets_tenant_created",
        "media_assets",
        ["tenant_id", sa.text("created_at DESC")],
    )
    # Asset queries: JOIN with users for "uploaded by"
    op.create_index(
        "ix_media_assets_uploaded_by",
        "media_assets",
        ["uploaded_by"],
    )
    # AI usage: billing queries by tenant and date
    op.create_index(
        "ix_ai_usage_logs_tenant_created",
        "ai_usage_logs",
        ["tenant_id", sa.text("created_at DESC")],
    )
    # Webhooks: only active webhooks per tenant (partial index)
    op.execute(
        "CREATE INDEX ix_webhooks_tenant_active "
        "ON webhooks (tenant_id, is_active) "
        "WHERE is_active = true"
    )
    # Refresh statistics for the query planner
    op.execute("ANALYZE media_assets")
    op.execute("ANALYZE ai_usage_logs")
    op.execute("ANALYZE webhooks")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_webhooks_tenant_active")
    op.drop_index("ix_ai_usage_logs_tenant_created", table_name="ai_usage_logs")
    op.drop_index("ix_media_assets_uploaded_by", table_name="media_assets")
    op.drop_index("ix_media_assets_tenant_created", table_name="media_assets")
    op.drop_index("ix_media_assets_tenant_status", table_name="media_assets")
