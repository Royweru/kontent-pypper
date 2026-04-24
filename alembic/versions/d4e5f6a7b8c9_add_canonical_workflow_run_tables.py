"""add canonical workflow run tables

Revision ID: d4e5f6a7b8c9
Revises: c7d8e9f0a1b2
Create Date: 2026-04-23 14:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d4e5f6a7b8c9"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_key", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column("trigger_ref", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'queued'"), nullable=True),
        sa.Column("pipeline_node", sa.String(length=50), nullable=True),
        sa.Column("plan_tier", sa.String(length=20), nullable=True),
        sa.Column("video_model", sa.String(length=30), nullable=True),
        sa.Column("initial_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("final_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_runs_id", "workflow_runs", ["id"], unique=False)
    op.create_index("ix_workflow_runs_run_key", "workflow_runs", ["run_key"], unique=True)
    op.create_index("ix_workflow_runs_user_id", "workflow_runs", ["user_id"], unique=False)
    op.create_index("ix_workflow_runs_trigger_type", "workflow_runs", ["trigger_type"], unique=False)
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"], unique=False)

    op.create_table(
        "content_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_name", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("rank_score", sa.Float(), server_default=sa.text("0.0"), nullable=True),
        sa.Column("rank_features", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("selected", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["content_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_content_candidates_id", "content_candidates", ["id"], unique=False)
    op.create_index("ix_content_candidates_run_id", "content_candidates", ["run_id"], unique=False)
    op.create_index("ix_content_candidates_user_id", "content_candidates", ["user_id"], unique=False)
    op.create_index("ix_content_candidates_source_id", "content_candidates", ["source_id"], unique=False)
    op.create_index("ix_content_candidates_source_type", "content_candidates", ["source_type"], unique=False)
    op.create_index("ix_content_candidates_url", "content_candidates", ["url"], unique=False)
    op.create_index("ix_content_candidates_selected", "content_candidates", ["selected"], unique=False)

    op.create_table(
        "run_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("artifact_type", sa.String(length=30), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("media_url", sa.String(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.String(length=20), server_default=sa.text("'v1'"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_library.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_artifacts_id", "run_artifacts", ["id"], unique=False)
    op.create_index("ix_run_artifacts_run_id", "run_artifacts", ["run_id"], unique=False)
    op.create_index("ix_run_artifacts_artifact_type", "run_artifacts", ["artifact_type"], unique=False)
    op.create_index("ix_run_artifacts_platform", "run_artifacts", ["platform"], unique=False)

    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("node", sa.String(length=50), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_events_id", "run_events", ["id"], unique=False)
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"], unique=False)
    op.create_index("ix_run_events_node", "run_events", ["node"], unique=False)
    op.create_index("ix_run_events_event_type", "run_events", ["event_type"], unique=False)

    op.create_table(
        "quality_evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("criterion", sa.String(length=60), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quality_evaluations_id", "quality_evaluations", ["id"], unique=False)
    op.create_index("ix_quality_evaluations_run_id", "quality_evaluations", ["run_id"], unique=False)
    op.create_index("ix_quality_evaluations_criterion", "quality_evaluations", ["criterion"], unique=False)
    op.create_index("ix_quality_evaluations_passed", "quality_evaluations", ["passed"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quality_evaluations_passed", table_name="quality_evaluations")
    op.drop_index("ix_quality_evaluations_criterion", table_name="quality_evaluations")
    op.drop_index("ix_quality_evaluations_run_id", table_name="quality_evaluations")
    op.drop_index("ix_quality_evaluations_id", table_name="quality_evaluations")
    op.drop_table("quality_evaluations")

    op.drop_index("ix_run_events_event_type", table_name="run_events")
    op.drop_index("ix_run_events_node", table_name="run_events")
    op.drop_index("ix_run_events_run_id", table_name="run_events")
    op.drop_index("ix_run_events_id", table_name="run_events")
    op.drop_table("run_events")

    op.drop_index("ix_run_artifacts_platform", table_name="run_artifacts")
    op.drop_index("ix_run_artifacts_artifact_type", table_name="run_artifacts")
    op.drop_index("ix_run_artifacts_run_id", table_name="run_artifacts")
    op.drop_index("ix_run_artifacts_id", table_name="run_artifacts")
    op.drop_table("run_artifacts")

    op.drop_index("ix_content_candidates_selected", table_name="content_candidates")
    op.drop_index("ix_content_candidates_url", table_name="content_candidates")
    op.drop_index("ix_content_candidates_source_type", table_name="content_candidates")
    op.drop_index("ix_content_candidates_source_id", table_name="content_candidates")
    op.drop_index("ix_content_candidates_user_id", table_name="content_candidates")
    op.drop_index("ix_content_candidates_run_id", table_name="content_candidates")
    op.drop_index("ix_content_candidates_id", table_name="content_candidates")
    op.drop_table("content_candidates")

    op.drop_index("ix_workflow_runs_status", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_trigger_type", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_user_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_run_key", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")

