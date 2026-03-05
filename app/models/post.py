"""
KontentPyper - Post & PostResult Models
Tracks every publish action and its per-platform outcome.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    original_content = Column(Text, nullable=False)
    enhanced_content = Column(JSONB, nullable=True)

    image_urls = Column(Text, nullable=True)
    video_urls = Column(Text, nullable=True)
    audio_file_url = Column(String, nullable=True)

    platform_specific_content = Column(JSONB, nullable=True)
    platforms = Column(Text, nullable=False)

    status = Column(String, server_default=text("'processing'"))
    scheduled_for = Column(DateTime, nullable=True, index=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    # ── Relationships ─────────────────────────────────────────────
    user = relationship("User", back_populates="posts")
    post_results = relationship(
        "PostResult", back_populates="post", cascade="all, delete-orphan"
    )
    analytics = relationship(
        "PostAnalytics", back_populates="post", cascade="all, delete-orphan"
    )
    template_analytics = relationship(
        "TemplateAnalytics", back_populates="post", cascade="all, delete-orphan"
    )


class PostResult(Base):
    __tablename__ = "post_results"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    platform = Column(String, nullable=False)
    status = Column(String, server_default=text("'pending'"))
    platform_post_id = Column(String, nullable=True)
    platform_post_url = Column(String, nullable=True)
    content_used = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, server_default=text("0"))

    posted_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    post = relationship("Post", back_populates="post_results")
