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
from urllib.parse import parse_qs, urlparse

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


def _as_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _default_ssl_mode(database_url: str) -> str:
    host = (urlparse(database_url).hostname or "").lower()
    if host.endswith(".neon.tech"):
        return "require"
    return "prefer"


def _build_connect_args(database_url: str) -> dict:
    parsed = urlparse(database_url)
    query = parse_qs(parsed.query)

    ssl_mode = (
        os.getenv("DB_SSL_MODE")
        or query.get("ssl", [None])[0]
        or query.get("sslmode", [None])[0]
        or _default_ssl_mode(database_url)
    )
    ssl_mode = (ssl_mode or "prefer").strip().lower()
    allowed_ssl_modes = {
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
    }
    if ssl_mode not in allowed_ssl_modes:
        raise ValueError(
            "Invalid DB_SSL_MODE. Use one of: disable, allow, prefer, "
            "require, verify-ca, verify-full"
        )

    connect_args = {
        "ssl": ssl_mode,
        "timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "45")),
        "command_timeout": int(os.getenv("DB_COMMAND_TIMEOUT", "45")),
        "statement_cache_size": 0,
        "server_settings": {
            "application_name": "kontentpyper",
            "jit": "off",
        },
    }

    # Some networks/proxies reset STARTTLS upgrades; direct TLS can avoid that.
    if _as_bool("DB_DIRECT_TLS", default=False):
        connect_args["direct_tls"] = True

    return connect_args


ASYNC_DATABASE_URL = _build_async_url()


engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_use_lifo=True,
    pool_recycle=120,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "2")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    connect_args=_build_connect_args(ASYNC_DATABASE_URL),
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
