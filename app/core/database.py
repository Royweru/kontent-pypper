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
from dotenv import load_dotenv


load_dotenv()

def _build_async_url() -> str:
    """Convert a standard DATABASE_URL into asyncpg format."""
    raw = os.getenv("DATABASE_URL","is_empty")
    if not raw:
        raise ValueError("DATABASE_URL environment variable is not set")
    base = raw.split("?")[0]

    if base.startswith("postgresql://"):
        return base.replace("postgresql://", "postgresql+asyncpg://", 1)
    return base


engine = create_async_engine(
    _build_async_url(),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    connect_args={
        "ssl": "require",
        "timeout": 60,
        "command_timeout": 60,
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
