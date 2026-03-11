"""
KontentPyper - Content Source Models
Tracks fetched articles from RSS and Reddit.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.sql import text
from app.core.database import Base


class ContentItem(Base):
    """
    Stores individual news/content items fetched from RSS/Reddit.

    Scope: A content item can be global (user_id=NULL, source_id=NULL) from the
    background ingest job, or user-scoped (user_id set) from a personalized feed.
    The URL uniqueness constraint is intentionally removed so the same article
    can appear independently for different users from their own sources.
    """
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)

    # Optional relation to a specific user (personalized) or null for global feed
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    # Back-link to the ContentSource row that produced this item.
    # SET NULL on delete so items survive source removal.
    source_id = Column(
        Integer, ForeignKey("content_sources.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    title = Column(String, nullable=False)
    url = Column(String, nullable=False, index=True)
    source_name = Column(String, nullable=False)   # e.g. "TechCrunch", "r/tech"
    source_type = Column(String, nullable=False)   # "rss" | "reddit"
    image_url = Column(String, nullable=True)      # og:image / Reddit thumbnail

    snippet = Column(Text, nullable=True)          # Summary or Reddit post body
    published_date = Column(DateTime, nullable=True)

    relevance_score = Column(Float, server_default=text("0.0"))
    is_used = Column(Boolean, server_default=text("false"))

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )


class ApprovalQueue(Base):
    """
    Queue for Telegram Human-in-the-loop (HITL) video approvals.
    """
    __tablename__ = "approval_queue"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_item_id = Column(Integer, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)

    video_path = Column(String, nullable=False)
    script_text = Column(Text, nullable=False)

    telegram_message_id = Column(String, nullable=True)

    # 'pending' | 'approved' | 'rejected'
    status = Column(String, server_default=text("'pending'"))
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )
