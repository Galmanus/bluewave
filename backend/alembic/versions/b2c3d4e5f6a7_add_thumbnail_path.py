"""add_thumbnail_path_to_media_assets

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'media_assets',
        sa.Column(
            'thumbnail_path',
            sa.String(512),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('media_assets', 'thumbnail_path')
