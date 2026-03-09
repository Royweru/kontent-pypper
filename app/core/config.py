"""
KontentPyper - Application Configuration
Reads all environment variables via Pydantic Settings.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Application Identity ──────────────────────────────────────
    APP_NAME: str = "KontentPypper"
    DEBUG: bool = False

    # ── Database (Neon PostgreSQL) ────────────────────────────────
    DATABASE_URL: str = ""

    # ── JWT Authentication ────────────────────────────────────────
    SECRET_KEY: str = "change-me-to-a-real-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # ── AI / LLM Providers ────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    GOOGLE_GEMINI_API_KEY: str = ""

    # ── Social Platform: Twitter / X  (OAuth 1.0a) ───────────────
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: str = ""

    # ── Social Platform: LinkedIn (OAuth 2.0) ─────────────────────
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

    # ── Social Platform: YouTube / Google (OAuth 2.0) ─────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ── Social Platform: TikTok (OAuth 2.0 + PKCE) ───────────────
    TIKTOK_CLIENT_ID: str = ""
    TIKTOK_CLIENT_SECRET: str = ""

    # ── Social Platform: Facebook (OAuth 2.0) ─────────────────────
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""

    # ── Social Platform: Instagram (OAuth 2.0, via Facebook) ──────
    INSTAGRAM_CLIENT_ID: str = ""
    INSTAGRAM_CLIENT_SECRET: str = ""

    # ── Reddit (Content Source) ───────────────────────────────────
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "KontentPyper/1.0"

    # ── Pexels (Stock Media) ──────────────────────────────────────
    PEXELS_API_KEY: str = ""

    # ── Cloud Storage ─────────────────────────────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_BUCKET_NAME: str = "kontent"
    R2_PUBLIC_DEV_URL: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""

    UPLOAD_DIR: str = "uploads/"

    # ── Email / SMTP ──────────────────────────────────────────────
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "rythmcode13@gmail.com"
    FROM_NAME: str = "KontentPypper"

    # ── Telegram Notifications ────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # ── URLs ──────────────────────────────────────────────────────
    BACKEND_URL: str = "https://kontent-pypper.onrender.com"

    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # ── Video/Media Generation Defaults ───────────────────────────
    VIDEO_OUTPUT_DIR: str = "videos/"
    VIDEO_TEMP_DIR: str = "temp/"
    VIDEO_MAX_DURATION: int = 180
    VIDEO_DEFAULT_ASPECT: str = "9:16"

    OPENAI_TTS_MODEL: str = "tts-1"
    OPENAI_TTS_VOICE: str = "alloy"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
