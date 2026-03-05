"""
KontentPyper - Analytics Models
Per-post metrics, template performance, and user-level summaries.
"""

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Float, ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class PostAnalytics(Base):
    __tablename__ = "post_analytics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform = Column(String, nullable=False, index=True)

    # Core metrics
    views = Column(Integer, server_default=text("0"))
    impressions = Column(Integer, server_default=text("0"))
    reach = Column(Integer, server_default=text("0"))

    # Engagement metrics
    likes = Column(Integer, server_default=text("0"))
    comments = Column(Integer, server_default=text("0"))
    shares = Column(Integer, server_default=text("0"))
    saves = Column(Integer, server_default=text("0"))
    clicks = Column(Integer, server_default=text("0"))

    # Platform-specific blob
    platform_specific_metrics = Column(JSONB, nullable=True)

    engagement_rate = Column(Float, server_default=text("0.0"))

    # Metadata
    fetched_at = Column(
        DateTime,
        nullable=False,
        index=True,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    error = Column(Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("post_id", "platform", name="uq_post_platform"),
    )

    post = relationship("Post", back_populates="analytics")


class UserAnalyticsSummary(Base):
    __tablename__ = "user_analytics_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    period = Column(String, nullable=False, index=True)  # daily | weekly | monthly
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False)

    total_posts = Column(Integer, server_default=text("0"))
    total_engagements = Column(Integer, server_default=text("0"))
    total_impressions = Column(Integer, server_default=text("0"))
    avg_engagement_rate = Column(Float, server_default=text("0.0"))
    platform_breakdown = Column(JSONB, nullable=True)

    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id", "period", "start_date", name="uq_user_period_start"
        ),
    )

    user = relationship("User", back_populates="analytics_summaries")


class TemplateAnalytics(Base):
    __tablename__ = "template_analytics"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("post_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="SET NULL"),
        nullable=True,
    )

    views = Column(Integer, server_default=text("0"))
    likes = Column(Integer, server_default=text("0"))
    comments = Column(Integer, server_default=text("0"))
    shares = Column(Integer, server_default=text("0"))
    engagement_rate = Column(Integer, server_default=text("0"))

    platform = Column(String, nullable=False)
    posted_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

    template = relationship("PostTemplate", back_populates="template_analytics")
    post = relationship("Post", back_populates="template_analytics")
