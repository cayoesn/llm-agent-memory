import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/memory_engine"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async SQLAlchemy session per request."""
    async with AsyncSessionLocal() as session:
        yield session


# Exposed for use by the scheduler and background workers that need to create
# their own sessions outside of the request/response lifecycle.
async_session_factory = AsyncSessionLocal
