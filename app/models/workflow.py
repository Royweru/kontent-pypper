"""
KontentPyper - Canonical Workflow Run Models
Tracks unified orchestration runs, inputs, outputs, events, and quality checks.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_key = Column(String(36), nullable=False, unique=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_type = Column(String(30), nullable=False, index=True)
    trigger_ref = Column(String(120), nullable=True)

    status = Column(String(30), server_default=text("'queued'"), index=True)
    pipeline_node = Column(String(50), nullable=True)
    plan_tier = Column(String(20), nullable=True)
    video_model = Column(String(30), nullable=True)

    initial_state = Column(JSONB, nullable=True)
    final_state = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    events = relationship(
        "RunEvent", back_populates="run", cascade="all, delete-orphan"
    )
    artifacts = relationship(
        "RunArtifact", back_populates="run", cascade="all, delete-orphan"
    )
    evaluations = relationship(
        "QualityEvaluation", back_populates="run", cascade="all, delete-orphan"
    )


class ContentCandidate(Base):
    __tablename__ = "content_candidates"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id = Column(
        Integer,
        ForeignKey("content_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source_type = Column(String(20), nullable=False, index=True)
    source_name = Column(String, nullable=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False, index=True)
    summary = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)

    rank_score = Column(Float, server_default=text("0.0"))
    rank_features = Column(JSONB, nullable=True)
    selected = Column(Boolean, server_default=text("FALSE"), index=True)
    raw_payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class RunArtifact(Base):
    __tablename__ = "run_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id = Column(
        Integer,
        ForeignKey("asset_library.id", ondelete="SET NULL"),
        nullable=True,
    )

    artifact_type = Column(String(30), nullable=False, index=True)
    platform = Column(String(30), nullable=True, index=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    media_url = Column(String, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    version = Column(String(20), server_default=text("'v1'"))

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    run = relationship("WorkflowRun", back_populates="artifacts")


class RunEvent(Base):
    __tablename__ = "run_events"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node = Column(String(50), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    run = relationship("WorkflowRun", back_populates="events")


class QualityEvaluation(Base):
    __tablename__ = "quality_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(
        Integer,
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion = Column(String(60), nullable=False, index=True)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, server_default=text("FALSE"), index=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    run = relationship("WorkflowRun", back_populates="evaluations")

