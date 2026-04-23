"""add scheduled_jobs and extend asset_library

Revision ID: a5b8c3d4e6f7
Revises: f3a7b9c2d1e0
Create Date: 2026-04-20 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'a5b8c3d4e6f7'
down_revision = 'f3a7b9c2d1e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create scheduled_jobs table ─────────────────────────────────
    op.create_table(
        'scheduled_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('schedule_preset', sa.String(), server_default=sa.text("'daily_8am'")),
        sa.Column('cron_hour', sa.Integer(), server_default=sa.text("8")),
        sa.Column('cron_minute', sa.Integer(), server_default=sa.text("0")),
        sa.Column('cron_dow', sa.String(), server_default=sa.text("'*'")),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('total_runs', sa.Integer(), server_default=sa.text("0")),
        sa.Column('last_run_status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scheduled_jobs_id', 'scheduled_jobs', ['id'])
    op.create_index('ix_scheduled_jobs_user_id', 'scheduled_jobs', ['user_id'], unique=True)

    # ── Extend asset_library with review queue fields ───────────────
    with op.batch_alter_table('asset_library') as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(), server_default=sa.text("'draft'")))
        batch_op.add_column(sa.Column('platform_drafts', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('video_script_data', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('source_article_title', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('source_article_url', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('video_model_used', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('credits_consumed', sa.Integer(), server_default=sa.text("0")))
        batch_op.add_column(sa.Column('scheduled_publish_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('published_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('rejected_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('workflow_run_id', sa.String(), nullable=True))
        batch_op.create_index('ix_asset_library_status', ['status'])
        batch_op.create_index('ix_asset_library_workflow_run_id', ['workflow_run_id'])


def downgrade() -> None:
    with op.batch_alter_table('asset_library') as batch_op:
        batch_op.drop_index('ix_asset_library_workflow_run_id')
        batch_op.drop_index('ix_asset_library_status')
        batch_op.drop_column('workflow_run_id')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('rejected_at')
        batch_op.drop_column('published_at')
        batch_op.drop_column('scheduled_publish_at')
        batch_op.drop_column('credits_consumed')
        batch_op.drop_column('video_model_used')
        batch_op.drop_column('source_article_url')
        batch_op.drop_column('source_article_title')
        batch_op.drop_column('video_script_data')
        batch_op.drop_column('platform_drafts')
        batch_op.drop_column('status')

    op.drop_index('ix_scheduled_jobs_user_id', table_name='scheduled_jobs')
    op.drop_index('ix_scheduled_jobs_id', table_name='scheduled_jobs')
    op.drop_table('scheduled_jobs')
