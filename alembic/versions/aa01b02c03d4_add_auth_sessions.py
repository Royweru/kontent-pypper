"""add auth sessions

Revision ID: aa01b02c03d4
Revises: cb56b020daea
Create Date: 2026-04-27 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "aa01b02c03d4"
down_revision: Union[str, Sequence[str], None] = "cb56b020daea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_key", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("is_revoked", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_hash"),
        sa.UniqueConstraint("session_key"),
    )
    op.create_index("ix_auth_sessions_id", "auth_sessions", ["id"], unique=False)
    op.create_index("ix_auth_sessions_session_key", "auth_sessions", ["session_key"], unique=True)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)
    op.create_index("ix_auth_sessions_refresh_token_hash", "auth_sessions", ["refresh_token_hash"], unique=True)
    op.create_index("ix_auth_sessions_is_revoked", "auth_sessions", ["is_revoked"], unique=False)
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_is_revoked", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_refresh_token_hash", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_session_key", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
