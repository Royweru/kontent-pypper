"""
KontentPyper - User & Subscription Models
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Auth metadata
    auth_provider = Column(String, nullable=True, default="email")
    last_login_method = Column(String, nullable=True)

    # Email verification
    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, nullable=True)
    email_verification_expires = Column(DateTime, nullable=True)

    # Password reset
    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)

    # Account state
    is_active = Column(Boolean, default=True)
    plan = Column(String, default="trial")
    trial_ends_at = Column(DateTime, nullable=True)
    posts_used = Column(Integer, server_default=text("0"))
    posts_limit = Column(Integer, server_default=text("10"))

    # Timestamps
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )
    last_login = Column(DateTime, nullable=True)

    # Notification prefs
    email_on_post_success = Column(Boolean, server_default=text("TRUE"))
    email_on_post_failure = Column(Boolean, server_default=text("TRUE"))
    email_weekly_analytics = Column(Boolean, server_default=text("TRUE"))

    # ── Relationships ─────────────────────────────────────────────
    social_connections = relationship(
        "SocialConnection", back_populates="user", cascade="all, delete-orphan"
    )
    posts = relationship(
        "Post", back_populates="user", cascade="all, delete-orphan"
    )
    post_templates = relationship(
        "PostTemplate", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    template_folders = relationship(
        "TemplateFolder", back_populates="user", cascade="all, delete-orphan"
    )
    analytics_summaries = relationship(
        "UserAnalyticsSummary", back_populates="user", cascade="all, delete-orphan"
    )
    content_sources = relationship(
        "ContentSource", back_populates="user", cascade="all, delete-orphan"
    )
    video_campaigns = relationship(
        "VideoCampaign", back_populates="user", cascade="all, delete-orphan"
    )
    story_contents = relationship(
        "StoryContent", back_populates="user", cascade="all, delete-orphan"
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    plan = Column(String, nullable=False)
    status = Column(String, server_default=text("'active'"))
    amount = Column(Integer, nullable=False)
    currency = Column(String, server_default=text("'USD'"))
    payment_method = Column(String, nullable=False)
    payment_reference = Column(String, nullable=True)

    starts_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    ends_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="subscriptions")
