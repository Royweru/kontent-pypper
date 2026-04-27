"""
KontentPyper - Async Database Engine
Connects to Neon PostgreSQL via asyncpg with connection pooling.
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import os

load_dotenv()


def _build_async_url() -> str:
    """Convert DATABASE_URL to asyncpg format while preserving query params."""
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        raise ValueError("DATABASE_URL environment variable is not set")

    # Normalize old postgres:// URLs and keep full suffix/query untouched.
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql://", 1)

    if raw.startswith("postgresql+asyncpg://"):
        return raw
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


engine = create_async_engine(
    _build_async_url(),
    echo=False,
    pool_pre_ping=True,
    pool_use_lifo=True,
    pool_recycle=120,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "2")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    connect_args={
        # Neon/managed Postgres frequently needs explicit SSL + larger handshake windows.
        "ssl": "require",
        "timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "45")),
        "command_timeout": int(os.getenv("DB_COMMAND_TIMEOUT", "45")),
        "statement_cache_size": 0,
        "server_settings": {
            "application_name": "kontentpyper",
            "jit": "off",
        },
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db():
    """FastAPI dependency yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            raise
        finally:
            await session.close()
