"""add source_name logo_url category to content_sources

Revision ID: a1b2c3d4e5f6
Revises: e76da06b1cef
Create Date: 2026-03-11 10:19:00.000000

Adds three new nullable columns to content_sources:
  - source_name  : human-readable display label ("TechCrunch", "r/technology")
  - logo_url     : CDN logo/favicon URL for UI card display
  - category     : niche tag (tech | business | news | entertainment | real_estate | science | art_media)

All columns are nullable so existing rows need no backfill.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9eb226871692'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'content_sources',
        sa.Column('source_name', sa.String(), nullable=True),
    )
    op.add_column(
        'content_sources',
        sa.Column('logo_url', sa.String(), nullable=True),
    )
    op.add_column(
        'content_sources',
        sa.Column('category', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('content_sources', 'category')
    op.drop_column('content_sources', 'logo_url')
    op.drop_column('content_sources', 'source_name')
