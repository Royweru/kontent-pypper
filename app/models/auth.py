"""
KontentPyper - Auth Session Models
Stores revocable refresh-token sessions without persisting raw tokens.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.core.database import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_key = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    refresh_token_hash = Column(String(64), nullable=False, unique=True, index=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)

    is_revoked = Column(Boolean, server_default=text("FALSE"), index=True)
    revoked_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="auth_sessions")


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_user_identities_provider_subject"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(32), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=False)
    email = Column(String, nullable=True, index=True)
    email_verified = Column(Boolean, server_default=text("FALSE"))
    display_name = Column(String, nullable=True)
    avatar_url = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="identities")
