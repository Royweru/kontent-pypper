"""
KontentPyper - Security Utilities
JWT encoding/decoding and password hashing via bcrypt.
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _prehash(plain: str) -> str:
    """SHA-256 pre-hash to bypass bcrypt's 72-byte limit.
    Always produces a 64-char hex string."""
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


# -- Password Hashing ---------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return bcrypt hash of a SHA-256 pre-hashed password."""
    return pwd_context.hash(_prehash(plain))


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain text against stored bcrypt hash (SHA-256 pre-hashed)."""
    # Try SHA-256 pre-hash first (new flow)
    if pwd_context.verify(_prehash(plain), hashed):
        return True
    # Fall back to raw verify for any passwords hashed before this change
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


# ── JWT Tokens ────────────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode a JWT access token with an expiry claim."""
    payload = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    Returns the payload dict or None if invalid/expired.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        return None
