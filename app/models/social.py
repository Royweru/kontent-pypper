"""
KontentPyper - SocialConnection Model
Stores OAuth tokens and platform metadata for each connected account.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class SocialConnection(Base):
    __tablename__ = "social_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    platform = Column(String, nullable=False, index=True)
    platform_user_id = Column(String, nullable=False)
    username = Column(String, nullable=False)

    # Auth protocol metadata
    protocol = Column(String, nullable=True)  # "oauth1" | "oauth2"
    oauth_token_secret = Column(Text, nullable=True)  # OAuth 1.0a only

    # Tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # Profile info
    platform_avatar_url = Column(String, nullable=True)
    platform_username = Column(String, nullable=True)

    # Sync state
    last_synced = Column(DateTime, nullable=True)
    is_active = Column(Boolean, server_default=text("TRUE"))

    # Timestamps
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    # Facebook page fields (only populated for FB connections)
    facebook_page_id = Column(String, nullable=True)
    facebook_page_name = Column(String, nullable=True)
    facebook_page_access_token = Column(Text, nullable=True)
    facebook_page_category = Column(String, nullable=True)
    facebook_page_picture = Column(String, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    user = relationship("User", back_populates="social_connections")
