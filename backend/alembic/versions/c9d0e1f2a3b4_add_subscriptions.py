"""add_subscriptions

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-03-18 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

plan_tier = postgresql.ENUM(
    'free', 'pro', 'business', 'enterprise',
    name='plan_tier',
    create_type=False,
)


def upgrade() -> None:
    plan_tier.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'tenant_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('tenants.id'), unique=True, nullable=False),
        sa.Column('plan', plan_tier, nullable=False, server_default='free'),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_users', sa.Integer, nullable=False, server_default='3'),
        sa.Column('max_ai_actions_month', sa.Integer, nullable=False, server_default='50'),
        sa.Column('max_storage_bytes', sa.BigInteger, nullable=False,
                   server_default=str(5 * 1024 ** 3)),
        sa.Column('created_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                   server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('tenant_subscriptions')
    plan_tier.drop(op.get_bind(), checkfirst=True)
