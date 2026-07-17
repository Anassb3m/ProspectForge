"""Async SQLAlchemy engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine_kwargs: dict = {"echo": settings.debug}
if settings.is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.database_url, **engine_kwargs)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create tables (dev/bootstrap). In production Alembic is the sole migration path."""
    from app import models  # noqa: F401

    if settings.is_production:
        # Production: Alembic is the only migration path.
        # entrypoint.sh runs `alembic upgrade head` and fails hard on error.
        # create_all() would silently create tables without migration tracking.
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
