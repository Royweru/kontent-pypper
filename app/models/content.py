"""
KontentPyper - Content Automation Models
Templates, folders, content sources, and scraped stories.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class PostTemplate(Base):
    __tablename__ = "post_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False, index=True)

    content_template = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)

    platform_variations = Column(JSON, nullable=True)
    supported_platforms = Column(JSON, nullable=False)

    tone = Column(String, server_default=text("'engaging'"))
    suggested_hashtags = Column(JSON, nullable=True)
    suggested_media_type = Column(String, nullable=True)

    # Visibility
    is_public = Column(Boolean, server_default=text("FALSE"))
    is_premium = Column(Boolean, server_default=text("FALSE"))
    is_system = Column(Boolean, server_default=text("FALSE"))

    # Performance tracking
    usage_count = Column(Integer, server_default=text("0"))
    success_rate = Column(Integer, server_default=text("0"))
    avg_engagement = Column(JSON, nullable=True)

    # Presentation
    thumbnail_url = Column(String, nullable=True)
    color_scheme = Column(String, server_default=text("'#3B82F6'"))
    icon = Column(String, server_default=text("'sparkles'"))
    is_favorite = Column(Boolean, server_default=text("FALSE"))

    folder_id = Column(
        Integer,
        ForeignKey("template_folders.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="post_templates")
    folder = relationship("TemplateFolder", back_populates="templates")
    template_analytics = relationship(
        "TemplateAnalytics", back_populates="template", cascade="all, delete-orphan"
    )


class TemplateFolder(Base):
    __tablename__ = "template_folders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String, server_default=text("'#6366F1'"))
    icon = Column(String, server_default=text("'folder'"))

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="template_folders")
    templates = relationship(
        "PostTemplate", back_populates="folder", cascade="all, delete-orphan"
    )


class ContentSource(Base):
    __tablename__ = "content_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_type = Column(String, nullable=False)  # reddit | rss | manual
    source_name = Column(String, nullable=True)   # Human-readable label e.g. "TechCrunch"
    source_url = Column(String, nullable=True)
    subreddit_name = Column(String, nullable=True)
    rss_feed_url = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)      # CDN logo/favicon URL for UI cards
    category = Column(String, nullable=True)      # niche: tech|business|news|entertainment|real_estate|science|art_media

    keywords_filter = Column(JSON, nullable=True)
    exclude_keywords = Column(JSON, nullable=True)
    min_score = Column(Integer, server_default=text("100"))
    max_age_hours = Column(Integer, server_default=text("24"))

    is_active = Column(Boolean, server_default=text("TRUE"))
    last_fetched = Column(DateTime, nullable=True)
    fetch_interval_hours = Column(Integer, server_default=text("6"))

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="content_sources")
    campaigns = relationship("VideoCampaign", back_populates="content_source")


class StoryContent(Base):
    __tablename__ = "story_contents"

    id = Column(Integer, primary_key=True, index=True)
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
    )

    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    source_type = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    author = Column(String, nullable=True)

    score = Column(Integer, server_default=text("0"))
    num_comments = Column(Integer, server_default=text("0"))

    is_used = Column(Boolean, server_default=text("FALSE"))
    used_in_job_id = Column(
        Integer,
        ForeignKey("video_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    fetched_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    user = relationship("User", back_populates="story_contents")

class AssetLibrary(Base):
    __tablename__ = "asset_library"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    asset_type = Column(String, nullable=False) # 'video', 'image', 'text'
    title = Column(String, nullable=True)
    content_url = Column(String, nullable=True) # S3 or local path for videos/images
    text_content = Column(Text, nullable=True) # For text assets like drafts
    
    file_size_bytes = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True) # For videos
    
    is_favorite = Column(Boolean, server_default=text("FALSE"))
    
    platforms_used = Column(JSON, nullable=True) # E.g., ['twitter', 'linkedin']
    
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    user = relationship("User", backref="assets")
