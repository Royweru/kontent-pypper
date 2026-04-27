"""add user identities

Revision ID: aa02b03c04d5
Revises: aa01b02c03d4
Create Date: 2026-04-27 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "aa02b03c04d5"
down_revision: Union[str, Sequence[str], None] = "aa01b02c03d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("email_verified", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_user_identities_provider_subject"),
    )
    op.create_index("ix_user_identities_id", "user_identities", ["id"], unique=False)
    op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"], unique=False)
    op.create_index("ix_user_identities_provider", "user_identities", ["provider"], unique=False)
    op.create_index("ix_user_identities_email", "user_identities", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_identities_email", table_name="user_identities")
    op.drop_index("ix_user_identities_provider", table_name="user_identities")
    op.drop_index("ix_user_identities_user_id", table_name="user_identities")
    op.drop_index("ix_user_identities_id", table_name="user_identities")
    op.drop_table("user_identities")
