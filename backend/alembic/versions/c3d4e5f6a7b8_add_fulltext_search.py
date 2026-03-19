"""add_fulltext_search_tsvector

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tsvector column
    op.execute("ALTER TABLE media_assets ADD COLUMN search_vector tsvector")

    # Create GIN index for fast full-text search
    op.execute("CREATE INDEX ix_media_assets_search ON media_assets USING gin(search_vector)")

    # Create trigger function that auto-updates search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION media_assets_search_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.caption, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(array_to_string(NEW.hashtags, ' '), '')), 'B') ||
                setweight(to_tsvector('english', coalesce(split_part(NEW.file_path, '/', -1), '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Create trigger on INSERT and UPDATE of relevant columns
    op.execute("""
        CREATE TRIGGER media_assets_search_trigger
        BEFORE INSERT OR UPDATE OF caption, hashtags, file_path
        ON media_assets
        FOR EACH ROW EXECUTE FUNCTION media_assets_search_update()
    """)

    # Backfill existing rows
    op.execute("""
        UPDATE media_assets SET search_vector =
            setweight(to_tsvector('english', coalesce(caption, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(array_to_string(hashtags, ' '), '')), 'B') ||
            setweight(to_tsvector('english', coalesce(split_part(file_path, '/', -1), '')), 'C')
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS media_assets_search_trigger ON media_assets")
    op.execute("DROP FUNCTION IF EXISTS media_assets_search_update()")
    op.execute("DROP INDEX IF EXISTS ix_media_assets_search")
    op.execute("ALTER TABLE media_assets DROP COLUMN IF EXISTS search_vector")
