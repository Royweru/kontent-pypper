"""
KontentPyper - Email Verification Service
Generates verification tokens and sends verification emails.
"""

import asyncio
import logging
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_token
from app.models.user import User

logger = logging.getLogger(__name__)


class EmailVerificationService:
    @staticmethod
    def _new_token() -> str:
        return secrets.token_urlsafe(48)

    @staticmethod
    async def issue_token(db: AsyncSession, user: User) -> str:
        raw_token = EmailVerificationService._new_token()
        user.email_verification_token = hash_token(raw_token)
        user.email_verification_expires = datetime.utcnow() + timedelta(
            hours=settings.EMAIL_VERIFICATION_TOKEN_HOURS
        )
        await db.commit()
        await db.refresh(user)
        return raw_token

    @staticmethod
    async def verify_token(db: AsyncSession, raw_token: str) -> User | None:
        token_hash = hash_token(raw_token)
        result = await db.execute(
            select(User).where(
                User.email_verification_token == token_hash,
                User.email_verification_expires > datetime.utcnow(),
            )
        )
        user = result.scalar_one_or_none()
        
        if not user: return None

        user.is_email_verified = True
        user.email_verification_token = None
        user.email_verification_expires = None
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def send_verification_email(user: User, verification_url: str) -> bool:
        """
        Send the verification email.
        Returns False when SMTP is not configured so local development can continue.
        """
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.warning(
                "[EmailVerification] SMTP not configured. Verification link for user_id=%s: %s",
                user.id,
                verification_url,
            )
            return False

        message = EmailMessage()
        message["Subject"] = "Verify your KontentPyper email"
        message["From"] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
        message["To"] = user.email
        message.set_content(
            "Verify your email to unlock KontentPyper automation.\n\n"
            f"{verification_url}\n\n"
            "This link expires in "
            f"{settings.EMAIL_VERIFICATION_TOKEN_HOURS} hours."
        )

        await asyncio.to_thread(EmailVerificationService._send_smtp, message)
        return True

    @staticmethod
    def _send_smtp(message: EmailMessage) -> None:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
