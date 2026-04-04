"""add credit tier fields and credit_transactions table

Revision ID: f3a7b9c2d1e0
Revises: 9eb226871692
Create Date: 2026-04-03 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a7b9c2d1e0'
down_revision: str = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add credit/tier columns to users table ────────────────────────
    op.add_column('users', sa.Column('tier_level', sa.String(), server_default=sa.text("'free'"), nullable=True))
    op.add_column('users', sa.Column('video_credits_remaining', sa.Integer(), server_default=sa.text("0"), nullable=True))
    op.add_column('users', sa.Column('video_credits_used_this_month', sa.Integer(), server_default=sa.text("0"), nullable=True))
    op.add_column('users', sa.Column('credits_reset_date', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('workflow_runs_today', sa.Integer(), server_default=sa.text("0"), nullable=True))
    op.add_column('users', sa.Column('workflow_runs_reset_date', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('active_niche', sa.String(), nullable=True))

    # ── Create credit_transactions table ──────────────────────────────
    op.create_table(
        'credit_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('credits_delta', sa.Integer(), nullable=False),
        sa.Column('credits_before', sa.Integer(), nullable=False),
        sa.Column('credits_after', sa.Integer(), nullable=False),
        sa.Column('model_used', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_credit_transactions_id'), 'credit_transactions', ['id'], unique=False)
    op.create_index(op.f('ix_credit_transactions_user_id'), 'credit_transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_credit_transactions_action_type'), 'credit_transactions', ['action_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_credit_transactions_action_type'), table_name='credit_transactions')
    op.drop_index(op.f('ix_credit_transactions_user_id'), table_name='credit_transactions')
    op.drop_index(op.f('ix_credit_transactions_id'), table_name='credit_transactions')
    op.drop_table('credit_transactions')

    op.drop_column('users', 'active_niche')
    op.drop_column('users', 'workflow_runs_reset_date')
    op.drop_column('users', 'workflow_runs_today')
    op.drop_column('users', 'credits_reset_date')
    op.drop_column('users', 'video_credits_used_this_month')
    op.drop_column('users', 'video_credits_remaining')
    op.drop_column('users', 'tier_level')
