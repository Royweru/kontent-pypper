"""
KontentPyper - Account Verification Guards
Shared checks for actions that should require a verified email address.
"""

from fastapi import HTTPException, status

from app.core.config import settings
from app.models.user import User


def require_verified_email(user: User) -> None:
    if not settings.REQUIRE_EMAIL_VERIFICATION:
        return
    if user.is_email_verified:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "email_not_verified",
            "message": "Verify your email before using automation, publishing, or social account connections.",
        },
    )
