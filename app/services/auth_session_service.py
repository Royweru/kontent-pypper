"""
KontentPyper - Auth Session Service
Creates and revokes refresh-token sessions.
"""

import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_refresh_token, hash_token
from app.models.auth import AuthSession


class AuthSessionService:
    @staticmethod
    async def create_session(
        db: AsyncSession,
        *,
        user_id: int,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[AuthSession, str]:
        """Create a persisted refresh session and return the raw refresh token once."""
        raw_refresh_token = create_refresh_token()
        session = AuthSession(
            session_key=secrets.token_urlsafe(32),
            user_id=user_id,
            refresh_token_hash=hash_token(raw_refresh_token),
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session, raw_refresh_token

    @staticmethod
    async def get_active_session_by_refresh_token(
        db: AsyncSession,
        refresh_token: str,
    ) -> AuthSession | None:
        token_hash = hash_token(refresh_token)
        result = await db.execute(
            select(AuthSession).where(
                AuthSession.refresh_token_hash == token_hash,
                AuthSession.is_revoked == False,
                AuthSession.expires_at > datetime.utcnow(),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke_session(db: AsyncSession, session: AuthSession) -> None:
        session.is_revoked = True
        session.revoked_at = datetime.utcnow()
        await db.commit()

    @staticmethod
    async def rotate_session(
        db: AsyncSession,
        session: AuthSession,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> str:
        """Rotate the refresh token for an active session."""
        raw_refresh_token = create_refresh_token()
        session.refresh_token_hash = hash_token(raw_refresh_token)
        session.user_agent = user_agent or session.user_agent
        session.ip_address = ip_address or session.ip_address
        session.last_used_at = datetime.utcnow()
        session.expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_DAYS)
        await db.commit()
        await db.refresh(session)
        return raw_refresh_token
