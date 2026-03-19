"""add_ai_usage_logs

Revision ID: a1b2c3d4e5f6
Revises: f933fe3e13ea
Create Date: 2026-03-17 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f933fe3e13ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum type used by the action_type column
ai_action_type = postgresql.ENUM(
    'caption', 'hashtags', 'compliance_check', 'auto_tag',
    'brand_voice', 'content_brief', 'resize',
    name='ai_action_type',
    create_type=False,
)


def upgrade() -> None:
    # Create the enum type first
    ai_action_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'ai_usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('users.id'), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('media_assets.id', ondelete='SET NULL'),
                   nullable=True),
        sa.Column('action_type', ai_action_type, nullable=False),
        sa.Column('model_used', sa.String(100), nullable=False),
        sa.Column('input_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('cost_millicents', sa.BigInteger, nullable=False, server_default='0',
                   comment='Cost in 1/1000 of a cent for precise billing aggregation'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        'ix_ai_usage_tenant_created', 'ai_usage_logs',
        ['tenant_id', 'created_at'],
    )
    op.create_index(
        'ix_ai_usage_tenant_action', 'ai_usage_logs',
        ['tenant_id', 'action_type'],
    )


def downgrade() -> None:
    op.drop_index('ix_ai_usage_tenant_action', table_name='ai_usage_logs')
    op.drop_index('ix_ai_usage_tenant_created', table_name='ai_usage_logs')
    op.drop_table('ai_usage_logs')
    ai_action_type.drop(op.get_bind(), checkfirst=True)
