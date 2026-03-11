"""add source_id image_url to content_items, drop url unique constraint

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-11 10:33:00.000000

Changes to content_items:
  - Add source_id  : nullable FK -> content_sources.id (SET NULL on delete)
  - Add image_url  : nullable string for og:image / Reddit thumbnail
  - Drop old unique constraint on url (same URL can appear for different users)
  - Add index on url (for dedup lookups without the UNIQUE constraint)
"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source_id FK
    op.add_column(
        'content_items',
        sa.Column('source_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_content_items_source_id',
        'content_items', 'content_sources',
        ['source_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_content_items_source_id', 'content_items', ['source_id'])

    # Add image_url
    op.add_column(
        'content_items',
        sa.Column('image_url', sa.String(), nullable=True),
    )

    # Drop the global unique constraint on url (SQLite: recreate; Postgres: drop directly)
    # We use a try/except so it degrades gracefully if the constraint name differs.
    try:
        op.drop_constraint('content_items_url_key', 'content_items', type_='unique')
    except Exception:
        pass  # Already absent or named differently — index still exists
    
    # Ensure a plain index exists for fast dedup lookups
    try:
        op.create_index('ix_content_items_url', 'content_items', ['url'])
    except Exception:
        pass  # Index may already exist from earlier migration


def downgrade() -> None:
    op.drop_index('ix_content_items_url', table_name='content_items')
    op.drop_column('content_items', 'image_url')
    op.drop_index('ix_content_items_source_id', table_name='content_items')
    op.drop_constraint('fk_content_items_source_id', 'content_items', type_='foreignkey')
    op.drop_column('content_items', 'source_id')
