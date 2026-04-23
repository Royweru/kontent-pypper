"""
KontentPyper - VideoCampaign & VideoJob Models
Automated video generation campaigns and their individual jobs.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class VideoCampaign(Base):
    __tablename__ = "video_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_source_id = Column(
        Integer,
        ForeignKey("content_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Video config
    video_style = Column(String, server_default=text("'ai_images_motion'"))
    aspect_ratio = Column(String, server_default=text("'9:16'"))
    duration_seconds = Column(Integer, server_default=text("60"))

    # TTS config
    tts_provider = Column(String, server_default=text("'openai'"))
    tts_voice = Column(String, server_default=text("'alloy'"))
    tts_speed = Column(Float, server_default=text("1.0"))

    # Audio
    background_music_url = Column(String, nullable=True)
    music_volume = Column(Float, server_default=text("0.3"))

    # Captions
    caption_style = Column(String, server_default=text("'modern'"))
    caption_font = Column(String, server_default=text("'Montserrat'"))
    caption_color = Column(String, server_default=text("'#FFFFFF'"))
    caption_position = Column(String, server_default=text("'bottom'"))

    # Scheduling
    auto_generate = Column(Boolean, server_default=text("TRUE"))
    videos_per_day = Column(Integer, server_default=text("2"))
    preferred_times = Column(JSON, nullable=True)
    platforms = Column(JSON, nullable=False)

    # State
    status = Column(String, server_default=text("'active'"))
    videos_generated = Column(Integer, server_default=text("0"))
    last_generation = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="video_campaigns")
    content_source = relationship("ContentSource", back_populates="campaigns")
    video_jobs = relationship(
        "VideoJob", back_populates="campaign", cascade="all, delete-orphan"
    )


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer,
        ForeignKey("video_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source material
    source_url = Column(String, nullable=True)
    source_title = Column(String, nullable=True)
    source_content = Column(Text, nullable=True)

    # Generated artifacts
    script_text = Column(Text, nullable=True)
    script_scenes = Column(JSON, nullable=True)
    narration_url = Column(String, nullable=True)
    narration_duration = Column(Float, nullable=True)
    image_prompts = Column(JSON, nullable=True)
    image_urls = Column(JSON, nullable=True)
    video_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    video_duration = Column(Float, nullable=True)

    # Pipeline state
    status = Column(String, server_default=text("'pending'"))
    progress = Column(Integer, server_default=text("0"))
    error_message = Column(Text, nullable=True)

    # Publishing
    platforms = Column(JSON, nullable=True)
    platform_post_ids = Column(JSON, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    campaign = relationship("VideoCampaign", back_populates="video_jobs")


# ==============================================================================
# Autonomous Agent Campaign Models
# ==============================================================================


class AgentCampaign(Base):
    """
    Autonomous content campaign configuration.

    Each campaign defines a recurring agent workflow that:
      1. Fetches trending content from the user's niche/topic
      2. Runs the LangGraph pipeline to generate platform-specific drafts + media
      3. Either auto-publishes or stores for manual HITL review

    Scheduling:
      - Each active campaign registers a dedicated APScheduler cron job
        with job_id = f"campaign_cron_{id}" for clean lifecycle management.
      - Multiple campaigns per user are supported (Max tier only).

    Rate Limiting:
      - max_runs_per_day prevents runaway cron from burning credits.
      - runs_today resets at midnight UTC via the daily reset job.
    """
    __tablename__ = "agent_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Campaign identity ─────────────────────────────────────────────
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # ── Content strategy ──────────────────────────────────────────────
    niche = Column(String(255), nullable=False)  # e.g. "AI & Machine Learning"
    topic_instructions = Column(Text, nullable=True)
    # Optional free-form prompt to guide the agent beyond the niche keyword.
    # e.g. "Focus on practical tutorials, avoid hype pieces"

    # ── Target platforms ──────────────────────────────────────────────
    target_platforms = Column(JSON, nullable=False, server_default=text("'[]'::jsonb"))
    # e.g. ["twitter", "linkedin", "tiktok"]

    # ── Publishing behavior ───────────────────────────────────────────
    auto_publish = Column(Boolean, server_default=text("FALSE"))
    # TRUE  = publish immediately after pipeline completes
    # FALSE = store in AssetLibrary as pending_review

    # ── Schedule configuration ────────────────────────────────────────
    schedule_preset = Column(String(50), server_default=text("'daily_8am'"))
    # Presets: daily_8am | daily_12pm | daily_6pm | weekdays_9am | custom
    cron_hour = Column(Integer, server_default=text("8"))
    cron_minute = Column(Integer, server_default=text("0"))
    cron_dow = Column(String(50), server_default=text("'*'"))
    # '*' = every day, 'mon,tue,wed,thu,fri' = weekdays only

    # ── Rate limiting ─────────────────────────────────────────────────
    max_runs_per_day = Column(Integer, server_default=text("3"))
    runs_today = Column(Integer, server_default=text("0"))
    runs_reset_date = Column(DateTime, nullable=True)

    # ── Resilience ────────────────────────────────────────────────────
    retry_on_failure = Column(Boolean, server_default=text("TRUE"))
    max_retries = Column(Integer, server_default=text("2"))
    consecutive_failures = Column(Integer, server_default=text("0"))
    # Auto-pauses campaign after 5 consecutive failures to prevent waste.

    # ── State ─────────────────────────────────────────────────────────
    status = Column(String(20), server_default=text("'active'"), index=True)
    # Values: active | paused | archived | error_paused
    is_active = Column(Boolean, server_default=text("TRUE"), index=True)

    # ── Tracking ──────────────────────────────────────────────────────
    total_runs = Column(Integer, server_default=text("0"))
    successful_runs = Column(Integer, server_default=text("0"))
    failed_runs = Column(Integer, server_default=text("0"))
    total_posts_published = Column(Integer, server_default=text("0"))
    total_credits_consumed = Column(Integer, server_default=text("0"))
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    # ── Relationships ─────────────────────────────────────────────────
    user = relationship("User", back_populates="agent_campaigns")
    runs = relationship(
        "AgentCampaignRun", back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="AgentCampaignRun.started_at.desc()",
    )


class AgentCampaignRun(Base):
    """
    Execution record for a single autonomous campaign run.

    Every time APScheduler fires a campaign cron job, a new row is
    inserted here with status='running'. The campaign_pipeline worker
    updates it as the pipeline progresses and finalizes the status.

    Designed for observability:
      - `pipeline_node` tracks which LangGraph node is currently executing
      - `error_details` stores structured JSON for debugging
      - `asset_id` links to the generated AssetLibrary entry
      - `platform_results` stores per-platform publish outcomes
    """
    __tablename__ = "agent_campaign_runs"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer,
        ForeignKey("agent_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id = Column(String(36), nullable=False, index=True)
    # UUID short string for log correlation across services

    # ── Pipeline state ────────────────────────────────────────────────
    status = Column(String(30), server_default=text("'running'"), index=True)
    # Values: running | success | failed | cancelled | publishing | published
    pipeline_node = Column(String(50), nullable=True)
    # Current/last node: fetch | score | draft | generate_media

    # ── Timing ────────────────────────────────────────────────────────
    started_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # ── Generated content ─────────────────────────────────────────────
    article_title = Column(String, nullable=True)
    article_url = Column(String, nullable=True)
    platform_drafts = Column(JSON, nullable=True)
    # { "twitter": "...", "linkedin": "...", "tiktok": "..." }
    video_url = Column(String, nullable=True)

    # ── Asset linkage ─────────────────────────────────────────────────
    asset_id = Column(
        Integer,
        ForeignKey("asset_library.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Publishing results ────────────────────────────────────────────
    auto_published = Column(Boolean, server_default=text("FALSE"))
    platform_results = Column(JSON, nullable=True)
    # [{ "platform": "twitter", "success": true, "post_url": "..." }, ...]

    # ── Credits ───────────────────────────────────────────────────────
    credits_consumed = Column(Integer, server_default=text("0"))
    video_model_used = Column(String(50), nullable=True)

    # ── Error handling ────────────────────────────────────────────────
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    # Structured error info: { "node": "...", "traceback": "...", "retry_count": 0 }

    # ── Timestamps ────────────────────────────────────────────────────
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    # ── Relationships ─────────────────────────────────────────────────
    campaign = relationship("AgentCampaign", back_populates="runs")
