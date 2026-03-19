"""add_langsmith_run_id_to_ai_usage_logs

Revision ID: f1a2b3c4d5e6
Revises: e2f3a4b5c6d7
Create Date: 2026-03-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ai_usage_logs',
        sa.Column(
            'langsmith_run_id',
            sa.String(64),
            nullable=True,
            comment='LangSmith trace run ID for linking feedback to AI outputs',
        ),
    )


def downgrade() -> None:
    op.drop_column('ai_usage_logs', 'langsmith_run_id')
