"""add_portals_and_automations

Revision ID: b7c8d9e0f1a2
Revises: 53cd94dadb9f
Create Date: 2026-03-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = '0e89aff23815'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

automation_trigger = postgresql.ENUM(
    'asset_uploaded', 'asset_submitted', 'asset_approved',
    'asset_rejected', 'compliance_checked',
    name='automation_trigger',
    create_type=False,
)


def upgrade() -> None:
    # -- Client Portals --
    op.create_table(
        'client_portals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('client_name', sa.String(255), nullable=False),
        sa.Column('client_logo_url', sa.String(512), nullable=True),
        sa.Column('primary_color', sa.String(7), nullable=False, server_default='#2563EB'),
        sa.Column('welcome_message', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'portal_collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('portal_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('client_portals.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_public', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'portal_collection_assets',
        sa.Column('collection_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('portal_collections.id'), primary_key=True),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('media_assets.id'), primary_key=True),
        sa.Column('added_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )

    # -- Automations --
    automation_trigger.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'automations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('trigger_type', automation_trigger, nullable=False),
        sa.Column('conditions', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('actions', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('run_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'automation_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('automation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('actions_executed', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('status', sa.String(20), nullable=False, server_default="'success'"),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('automation_logs')
    op.drop_table('automations')
    automation_trigger.drop(op.get_bind(), checkfirst=True)
    op.drop_table('portal_collection_assets')
    op.drop_table('portal_collections')
    op.drop_table('client_portals')
