"""
KontentPyper - Authentication API Routes
POST /login, POST /register, GET /me
"""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserResponse,
    TokenResponse,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: DB):
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
    return user


@router.post("/login", response_model=TokenResponse)
async def login(db: DB, form_data: OAuth2PasswordRequestForm = Depends()):
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
        expires_delta=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    return {"access_token": token, "token_type": "bearer"}


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
