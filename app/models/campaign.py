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
