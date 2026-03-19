"""add_all_new_tables_and_columns

Creates tables: asset_variants, asset_versions, asset_comments, content_briefs,
scheduled_posts, permissions.
Adds columns: thumbnail_path, captions_i18n, storage_region.

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-03-18 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- New columns on media_assets (thumbnail_path already added by b2c3d4e5f6a7) --
    op.add_column('media_assets', sa.Column('captions_i18n', postgresql.JSONB(), nullable=True, server_default='{}'))

    # -- New column on tenants --
    op.add_column('tenants', sa.Column('storage_region', sa.String(30), nullable=False, server_default='us-east-1'))

    # Tables asset_variants, asset_versions, asset_comments, content_briefs
    # already created by d4e5f6a7b8c9

    # -- scheduled_posts --
    op.create_table(
        'scheduled_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('media_assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('channel', sa.Enum('instagram', 'facebook', 'twitter', 'linkedin', 'tiktok', 'manual', name='post_channel'), nullable=False, server_default='manual'),
        sa.Column('caption_override', sa.Text(), nullable=True),
        sa.Column('hashtags_override', postgresql.ARRAY(sa.String), nullable=True),
        sa.Column('status', sa.Enum('scheduled', 'published', 'failed', 'cancelled', name='post_status'), nullable=False, server_default='scheduled'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('external_url', sa.String(512), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # -- permissions --
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resource_type', sa.Enum('portal', 'collection', 'all', name='resource_type'), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('permission', sa.Enum('view', 'edit', 'manage', 'admin', name='permission_level'), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('permissions')
    op.drop_table('scheduled_posts')
    op.drop_column('tenants', 'storage_region')
    op.drop_column('media_assets', 'captions_i18n')
    # Clean up enums owned by this migration
    op.execute("DROP TYPE IF EXISTS post_channel")
    op.execute("DROP TYPE IF EXISTS post_status")
    op.execute("DROP TYPE IF EXISTS resource_type")
    op.execute("DROP TYPE IF EXISTS permission_level")
