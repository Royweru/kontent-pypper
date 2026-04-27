"""
KontentPyper - Shared FastAPI Dependencies
get_db and get_current_user used across all protected routes.
"""

import asyncio
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
logger = logging.getLogger(__name__)


def _is_transient_db_error(exc: Exception) -> bool:
    """Best-effort detector for short-lived DB/network failures."""
    if isinstance(
        exc,
        (
            OperationalError,
            InterfaceError,
            DBAPIError,
            ConnectionResetError,
            TimeoutError,
            OSError,
        ),
    ):
        return True
    message = str(exc).lower()
    transient_tokens = (
        "winerror 10054",
        "winerror 64",
        "connection reset",
        "temporarily unavailable",
        "timed out",
    )
    return any(token in message for token in transient_tokens)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Validate JWT bearer token and return the authenticated User.
    Raises 401 if the token is missing, invalid, or expired.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exc

    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exc

    user = None
    for attempt in range(3):
        try:
            result = await db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            break
        except Exception as exc:
            if _is_transient_db_error(exc) and attempt < 2:
                backoff = 0.4 * (attempt + 1)
                logger.warning(
                    "[Auth] transient DB error while loading current user (attempt %d/3): %s",
                    attempt + 1,
                    exc,
                )
                await asyncio.sleep(backoff)
                continue
            if _is_transient_db_error(exc):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database temporarily unavailable. Please retry.",
                )
            raise

    if user is None or not user.is_active:
        raise credentials_exc

    return user


# Typed convenience alias for route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]
