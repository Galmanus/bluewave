"""add_variants_versions_comments_briefs

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-18 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- asset_variants (IMP-6) ---
    op.create_table(
        "asset_variants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format_name", sa.String(50), nullable=False),
        sa.Column("width", sa.Integer, nullable=False),
        sa.Column("height", sa.Integer, nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- asset_versions (IMP-9) ---
    op.create_table(
        "asset_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("caption", sa.Text, nullable=True),
        sa.Column("hashtags", ARRAY(sa.String), nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- asset_comments (IMP-10) ---
    op.create_table(
        "asset_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("asset_comments.id"), nullable=True),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_comments_asset_created", "asset_comments", ["asset_id", "created_at"])

    # --- content_briefs (IMP-16) ---
    op.create_table(
        "content_briefs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("brief_content", JSONB, nullable=True),
        sa.Column("suggested_asset_ids", ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column("status", sa.Enum("generating", "completed", "failed", name="brief_status", create_constraint=True), nullable=False, server_default="generating"),
        sa.Column("cost_millicents", sa.BigInteger, nullable=False, server_default="100000"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("content_briefs")
    op.execute("DROP TYPE IF EXISTS brief_status")
    op.drop_index("ix_comments_asset_created", table_name="asset_comments")
    op.drop_table("asset_comments")
    op.drop_table("asset_versions")
    op.drop_table("asset_variants")
