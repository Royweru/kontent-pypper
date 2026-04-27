"""
Google account login service.
Keeps account login separate from Google/YouTube social publishing OAuth.
"""

import re
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.auth import UserIdentity
from app.models.user import User


class GoogleAuthError(Exception):
    """Raised when the Google account login flow cannot be completed."""


class GoogleAuthService:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    STATE_PURPOSE = "google_account_login"

    @staticmethod
    def create_state() -> tuple[str, str]:
        """Return a signed state token and its nonce for cookie binding."""
        nonce = secrets.token_urlsafe(24)
        payload = {
            "purpose": GoogleAuthService.STATE_PURPOSE,
            "nonce": nonce,
            "exp": datetime.utcnow() + timedelta(minutes=10),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token, nonce

    @staticmethod
    def validate_state(state_token: str, expected_nonce: str | None) -> None:
        if not state_token or not expected_nonce:
            raise GoogleAuthError("Missing OAuth state.")

        try:
            payload = jwt.decode(
                state_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
        except JWTError as exc:
            raise GoogleAuthError("Invalid or expired OAuth state.") from exc

        if payload.get("purpose") != GoogleAuthService.STATE_PURPOSE:
            raise GoogleAuthError("Invalid OAuth state purpose.")
        if not secrets.compare_digest(str(payload.get("nonce", "")), expected_nonce):
            raise GoogleAuthError("OAuth state cookie mismatch.")

    @staticmethod
    def build_authorization_url(*, redirect_uri: str, state_token: str) -> str:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise GoogleAuthError("Google OAuth credentials are not configured.")

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state_token,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{GoogleAuthService.AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code_for_profile(*, code: str, redirect_uri: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_response = await client.post(
                GoogleAuthService.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            if token_response.status_code >= 400:
                raise GoogleAuthError("Google rejected the authorization code.")

            access_token = token_response.json().get("access_token")
            if not access_token:
                raise GoogleAuthError("Google did not return an access token.")

            profile_response = await client.get(
                GoogleAuthService.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if profile_response.status_code >= 400:
                raise GoogleAuthError("Could not fetch Google profile.")

        profile = profile_response.json()
        if not profile.get("sub"):
            raise GoogleAuthError("Google profile is missing subject.")
        if not profile.get("email"):
            raise GoogleAuthError("Google profile is missing email.")
        if profile.get("email_verified") not in (True, "true", "True", "1", 1):
            raise GoogleAuthError("Google account email is not verified.")
        return profile

    @staticmethod
    async def get_or_create_user(db: AsyncSession, profile: dict) -> User:
        provider_user_id = str(profile["sub"])
        email = str(profile["email"]).strip().lower()

        result = await db.execute(
            select(UserIdentity).where(
                UserIdentity.provider == "google",
                UserIdentity.provider_user_id == provider_user_id,
            )
        )
        identity = result.scalar_one_or_none()
        if identity:
            user = await db.get(User, identity.user_id)
            if not user:
                raise GoogleAuthError("Linked account no longer exists.")
            GoogleAuthService._update_user_from_google(user)
            GoogleAuthService._update_identity(identity, profile)
            await db.commit()
            await db.refresh(user)
            return user

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                username=await GoogleAuthService._unique_username(db, email),
                hashed_password=hash_password(secrets.token_urlsafe(32)),
                auth_provider="google",
                last_login_method="google",
                is_email_verified=True,
                is_active=True,
            )
            db.add(user)
            await db.flush()
        else:
            GoogleAuthService._update_user_from_google(user)

        db.add(
            UserIdentity(
                user_id=user.id,
                provider="google",
                provider_user_id=provider_user_id,
                email=email,
                email_verified=True,
                display_name=profile.get("name"),
                avatar_url=profile.get("picture"),
            )
        )
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    def _update_user_from_google(user: User) -> None:
        user.is_email_verified = True
        user.last_login_method = "google"
        user.last_login = datetime.utcnow()
        if not user.auth_provider:
            user.auth_provider = "google"

    @staticmethod
    def _update_identity(identity: UserIdentity, profile: dict) -> None:
        identity.email = str(profile.get("email") or identity.email).strip().lower()
        identity.email_verified = True
        identity.display_name = profile.get("name") or identity.display_name
        identity.avatar_url = profile.get("picture") or identity.avatar_url

    @staticmethod
    async def _unique_username(db: AsyncSession, email: str) -> str:
        base = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@", 1)[0]).lower()
        base = (base or "google_user")[:24]

        for index in range(1000):
            candidate = base if index == 0 else f"{base}{index}"
            result = await db.execute(select(User).where(User.username == candidate))
            if not result.scalar_one_or_none():
                return candidate

        return f"user_{secrets.token_hex(6)}"
