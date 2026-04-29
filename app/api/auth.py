"""
KontentPyper - Authentication API Routes
POST /login, POST /register, GET /me
"""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth_cookies import clear_auth_cookies, set_auth_cookies
from app.core.deps import DB, CurrentUser
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.services.auth_session_service import AuthSessionService
from app.services.email_verification_service import EmailVerificationService
from app.services.google_auth_service import GoogleAuthError, GoogleAuthService
from app.schemas.auth import (
    UserRegister,
    UserResponse,
    TokenResponse,
)

router = APIRouter()


def _verification_url(request: Request, token: str) -> str:
    return f"{request.url_for('verify_email')}?token={token}"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, request: Request, db: DB):
    """Create a new user account."""
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # Check username uniqueness
    existing_u = await db.execute(select(User).where(User.username == payload.username))
    if existing_u.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = await EmailVerificationService.issue_token(db, user)
    await EmailVerificationService.send_verification_email(
        user,
        _verification_url(request, token),
    )
    return user


@router.get("/verify-email", name="verify_email")
async def verify_email(token: str, db: DB):
    """Verify a user's email address from an emailed token."""
    user = await EmailVerificationService.verify_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )
    return {"success": True, "message": "Email verified. You can now use automation features."}


@router.post("/resend-verification")
async def resend_verification(request: Request, user: CurrentUser, db: DB):
    """Issue and send a fresh verification email for the current user."""
    if user.is_email_verified:
        return {"success": True, "message": "Email is already verified."}

    token = await EmailVerificationService.issue_token(db, user)
    sent = await EmailVerificationService.send_verification_email(
        user,
        _verification_url(request, token),
    )
    payload = {
        "success": True,
        "message": "Verification email sent." if sent else "Verification link generated.",
        "email_sent": sent,
    }
    if not sent:
        payload["verification_url"] = _verification_url(request, token)
    return payload


def _request_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def _google_redirect_uri(request: Request) -> str:
    if settings.GOOGLE_AUTH_REDIRECT_URI:
        return settings.GOOGLE_AUTH_REDIRECT_URI
    if settings.FRONTEND_URL:
        return f"{settings.FRONTEND_URL.rstrip('/')}/api/v1/auth/google/callback"
    return str(request.url_for("google_auth_callback"))


def _set_google_state_cookie(response: Response, nonce: str) -> None:
    cookie_options = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/api/v1/auth/google",
        "max_age": 600,
    }
    if settings.COOKIE_DOMAIN:
        cookie_options["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(settings.GOOGLE_AUTH_STATE_COOKIE_NAME, nonce, **cookie_options)


def _clear_google_state_cookie(response: Response) -> None:
    delete_options = {
        "path": "/api/v1/auth/google",
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }
    if settings.COOKIE_DOMAIN:
        delete_options["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(settings.GOOGLE_AUTH_STATE_COOKIE_NAME, **delete_options)


@router.get("/google/initiate")
async def initiate_google_login(request: Request, response: Response):
    """Create a Google account-login authorization URL."""
    try:
        state_token, nonce = GoogleAuthService.create_state()
        auth_url = GoogleAuthService.build_authorization_url(
            redirect_uri=_google_redirect_uri(request),
            state_token=state_token,
        )
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    _set_google_state_cookie(response, nonce)
    return {"auth_url": auth_url}


@router.get("/google/callback", name="google_auth_callback")
async def google_auth_callback(
    request: Request,
    db: DB,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """Complete Google account login, set auth cookies, and enter the dashboard."""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google login failed: {error}",
        )
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google authorization response.",
        )

    try:
        GoogleAuthService.validate_state(
            state,
            request.cookies.get(settings.GOOGLE_AUTH_STATE_COOKIE_NAME),
        )
        profile = await GoogleAuthService.exchange_code_for_profile(
            code=code,
            redirect_uri=_google_redirect_uri(request),
        )
        user = await GoogleAuthService.get_or_create_user(db, profile)
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    access_token = create_access_token(
        {"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_MINUTES),
    )
    _, refresh_token = await AuthSessionService.create_session(
        db,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=_request_ip(request),
    )

    redirect = RedirectResponse(f"{settings.FRONTEND_URL.rstrip('/')}/dashboard")
    set_auth_cookies(
        redirect,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    _clear_google_state_cookie(redirect)
    return redirect


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    db: DB,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Authenticate with email/username + password.
    Returns a JWT access token.
    """
    # Support login by email OR username
    result = await db.execute(
        select(User).where(
            (User.email == form_data.username) | (User.username == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    token = create_access_token(
        {"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_MINUTES),
    )
    _, refresh_token = await AuthSessionService.create_session(
        db,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=_request_ip(request),
    )
    set_auth_cookies(
        response,
        access_token=token,
        refresh_token=refresh_token,
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(request: Request, response: Response, db: DB):
    """Rotate refresh token and issue a fresh access token."""
    refresh_token = request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token.")

    session = await AuthSessionService.get_active_session_by_refresh_token(db, refresh_token)
    if not session:
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    result = await db.execute(select(User).where(User.id == session.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        await AuthSessionService.revoke_session(db, session)
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    access_token = create_access_token(
        {"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_MINUTES),
    )
    rotated_refresh = await AuthSessionService.rotate_session(
        db,
        session,
        user_agent=request.headers.get("user-agent"),
        ip_address=_request_ip(request),
    )
    set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=rotated_refresh,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(request: Request, response: Response, db: DB):
    """Revoke the current refresh session and clear auth cookies."""
    refresh_token = request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if refresh_token:
        session = await AuthSessionService.get_active_session_by_refresh_token(db, refresh_token)
        if session:
            await AuthSessionService.revoke_session(db, session)

    clear_auth_cookies(response)
    return {"success": True}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Return the currently authenticated user's profile."""
    return current_user


# ── Telegram Integration ──────────────────────────────────────────

from app.schemas.auth import TelegramSettings, TelegramDetectResponse


@router.get("/settings/telegram")
async def get_telegram_settings(user: CurrentUser):
    """Return the current user's Telegram integration status."""
    return {
        "has_bot_token": bool(user.telegram_bot_token),
        "chat_id": user.telegram_chat_id or None,
        "is_linked": bool(user.telegram_bot_token and user.telegram_chat_id),
    }


@router.put("/settings/telegram")
async def save_telegram_token(payload: TelegramSettings, user: CurrentUser, db: DB):
    """Save the Telegram bot token for the current user."""
    import httpx

    # Validate the token by calling getMe
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"https://api.telegram.org/bot{payload.bot_token}/getMe")

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid bot token. Please double-check it.")

    bot_info = resp.json().get("result", {})

    user.telegram_bot_token = payload.bot_token
    user.telegram_chat_id = None  # Clear old chat_id, user needs to re-link
    await db.commit()

    return {
        "success": True,
        "bot_username": bot_info.get("username", ""),
        "message": f"Bot @{bot_info.get('username', '')} saved. Now send /start to your bot in Telegram, then click Detect.",
    }


@router.post("/settings/telegram/detect", response_model=TelegramDetectResponse)
async def detect_telegram_chat(user: CurrentUser, db: DB):
    """
    Poll the Telegram getUpdates API to auto-detect the chat_id.
    The user must send /start to their bot before calling this.
    """
    import httpx

    if not user.telegram_bot_token:
        raise HTTPException(status_code=400, detail="No bot token configured. Save your bot token first.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.telegram.org/bot{user.telegram_bot_token}/getUpdates",
            params={"limit": 10, "timeout": 0}
        )

    if resp.status_code != 200:
        return TelegramDetectResponse(success=False, message="Failed to reach Telegram API. Check your bot token.")

    data = resp.json()
    updates = data.get("result", [])

    if not updates:
        return TelegramDetectResponse(
            success=False,
            message="No messages found. Please send /start to your bot in Telegram and try again."
        )

    # Find the most recent /start or any message
    chat_id = None
    chat_username = None

    for update in reversed(updates):
        msg = update.get("message", {})
        chat = msg.get("chat", {})
        if chat.get("id"):
            chat_id = str(chat["id"])
            chat_username = chat.get("username") or chat.get("first_name", "")
            break

    if not chat_id:
        return TelegramDetectResponse(
            success=False,
            message="Could not detect a chat. Send /start to your bot and try again."
        )

    # Save to database
    user.telegram_chat_id = chat_id
    await db.commit()

    return TelegramDetectResponse(
        success=True,
        chat_id=chat_id,
        username=chat_username,
        message=f"Linked to {chat_username} (chat {chat_id}). Telegram notifications are now active."
    )
