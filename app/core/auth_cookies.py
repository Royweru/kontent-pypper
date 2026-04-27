"""
KontentPyper - Auth Cookie Helpers
Centralizes cookie options for access and refresh tokens.
"""

from fastapi import Response

from app.core.config import settings


def _cookie_options(max_age: int) -> dict:
    options = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
        "max_age": max_age,
    }
    if settings.COOKIE_DOMAIN:
        options["domain"] = settings.COOKIE_DOMAIN
    return options


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str | None = None,
) -> None:
    """Attach auth cookies to a response."""
    response.set_cookie(
        settings.AUTH_ACCESS_COOKIE_NAME,
        access_token,
        **_cookie_options(settings.ACCESS_TOKEN_MINUTES * 60),
    )
    if refresh_token:
        response.set_cookie(
            settings.AUTH_REFRESH_COOKIE_NAME,
            refresh_token,
            **_cookie_options(settings.REFRESH_TOKEN_DAYS * 24 * 60 * 60),
        )


def clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies using the same domain/path attributes used to set them."""
    delete_options = {
        "path": "/",
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }
    if settings.COOKIE_DOMAIN:
        delete_options["domain"] = settings.COOKIE_DOMAIN

    response.delete_cookie(settings.AUTH_ACCESS_COOKIE_NAME, **delete_options)
    response.delete_cookie(settings.AUTH_REFRESH_COOKIE_NAME, **delete_options)
