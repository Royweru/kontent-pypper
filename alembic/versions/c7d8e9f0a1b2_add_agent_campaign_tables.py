"""add agent_campaigns and agent_campaign_runs tables

Revision ID: c7d8e9f0a1b2
Revises: a5b8c3d4e6f7
Create Date: 2026-04-22 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'c7d8e9f0a1b2'
down_revision = 'a5b8c3d4e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create agent_campaigns table ──────────────────────────────────
    op.create_table(
        'agent_campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),

        # Identity
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),

        # Content strategy
        sa.Column('niche', sa.String(255), nullable=False),
        sa.Column('topic_instructions', sa.Text(), nullable=True),

        # Target platforms
        sa.Column('target_platforms', postgresql.JSON(astext_type=sa.Text()),
                  nullable=False, server_default=sa.text("'[]'::jsonb")),

        # Publishing behavior
        sa.Column('auto_publish', sa.Boolean(), server_default=sa.text("FALSE")),

        # Schedule config
        sa.Column('schedule_preset', sa.String(50), server_default=sa.text("'daily_8am'")),
        sa.Column('cron_hour', sa.Integer(), server_default=sa.text("8")),
        sa.Column('cron_minute', sa.Integer(), server_default=sa.text("0")),
        sa.Column('cron_dow', sa.String(50), server_default=sa.text("'*'")),

        # Rate limiting
        sa.Column('max_runs_per_day', sa.Integer(), server_default=sa.text("3")),
        sa.Column('runs_today', sa.Integer(), server_default=sa.text("0")),
        sa.Column('runs_reset_date', sa.DateTime(), nullable=True),

        # Resilience
        sa.Column('retry_on_failure', sa.Boolean(), server_default=sa.text("TRUE")),
        sa.Column('max_retries', sa.Integer(), server_default=sa.text("2")),
        sa.Column('consecutive_failures', sa.Integer(), server_default=sa.text("0")),

        # State
        sa.Column('status', sa.String(20), server_default=sa.text("'active'")),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text("TRUE")),

        # Tracking
        sa.Column('total_runs', sa.Integer(), server_default=sa.text("0")),
        sa.Column('successful_runs', sa.Integer(), server_default=sa.text("0")),
        sa.Column('failed_runs', sa.Integer(), server_default=sa.text("0")),
        sa.Column('total_posts_published', sa.Integer(), server_default=sa.text("0")),
        sa.Column('total_credits_consumed', sa.Integer(), server_default=sa.text("0")),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_campaigns_id', 'agent_campaigns', ['id'])
    op.create_index('ix_agent_campaigns_user_id', 'agent_campaigns', ['user_id'])
    op.create_index('ix_agent_campaigns_status', 'agent_campaigns', ['status'])
    op.create_index('ix_agent_campaigns_is_active', 'agent_campaigns', ['is_active'])

    # ── Create agent_campaign_runs table ──────────────────────────────
    op.create_table(
        'agent_campaign_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.String(36), nullable=False),

        # Pipeline state
        sa.Column('status', sa.String(30), server_default=sa.text("'running'")),
        sa.Column('pipeline_node', sa.String(50), nullable=True),

        # Timing
        sa.Column('started_at', sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),

        # Generated content
        sa.Column('article_title', sa.String(), nullable=True),
        sa.Column('article_url', sa.String(), nullable=True),
        sa.Column('platform_drafts', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('video_url', sa.String(), nullable=True),

        # Asset linkage
        sa.Column('asset_id', sa.Integer(), nullable=True),

        # Publishing
        sa.Column('auto_published', sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column('platform_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),

        # Credits
        sa.Column('credits_consumed', sa.Integer(), server_default=sa.text("0")),
        sa.Column('video_model_used', sa.String(50), nullable=True),

        # Error handling
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),

        sa.ForeignKeyConstraint(['campaign_id'], ['agent_campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['asset_library.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_campaign_runs_id', 'agent_campaign_runs', ['id'])
    op.create_index('ix_agent_campaign_runs_campaign_id', 'agent_campaign_runs', ['campaign_id'])
    op.create_index('ix_agent_campaign_runs_run_id', 'agent_campaign_runs', ['run_id'])
    op.create_index('ix_agent_campaign_runs_status', 'agent_campaign_runs', ['status'])


def downgrade() -> None:
    # Drop agent_campaign_runs first (FK dependency)
    op.drop_index('ix_agent_campaign_runs_status', table_name='agent_campaign_runs')
    op.drop_index('ix_agent_campaign_runs_run_id', table_name='agent_campaign_runs')
    op.drop_index('ix_agent_campaign_runs_campaign_id', table_name='agent_campaign_runs')
    op.drop_index('ix_agent_campaign_runs_id', table_name='agent_campaign_runs')
    op.drop_table('agent_campaign_runs')

    # Drop agent_campaigns
    op.drop_index('ix_agent_campaigns_is_active', table_name='agent_campaigns')
    op.drop_index('ix_agent_campaigns_status', table_name='agent_campaigns')
    op.drop_index('ix_agent_campaigns_user_id', table_name='agent_campaigns')
    op.drop_index('ix_agent_campaigns_id', table_name='agent_campaigns')
    op.drop_table('agent_campaigns')
