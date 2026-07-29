"""Database-scoped acquisition locks.

PostgreSQL session advisory locks survive transaction commits, disappear when
the connection dies, and therefore cannot leave an expired Redis lease behind.
SQLite uses a process-local fallback only for deterministic unit tests.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_sqlite_guard = asyncio.Lock()
_sqlite_keys: set[str] = set()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def acquisition_run_lock(
    session: AsyncSession, key: str
) -> AsyncIterator[bool]:
    """Yield whether a non-blocking lock was acquired, then release safely."""
    dialect = session.bind.dialect.name if session.bind is not None else "unknown"
    acquired = False

    if dialect == "postgresql":
        acquired = bool(
            await session.scalar(
                text("SELECT pg_try_advisory_lock(hashtext(:lock_key))"),
                {"lock_key": key},
            )
        )
    else:
        async with _sqlite_guard:
            if key not in _sqlite_keys:
                _sqlite_keys.add(key)
                acquired = True

    try:
        yield acquired
    finally:
        if acquired:
            if dialect == "postgresql":
                try:
                    await session.scalar(
                        text("SELECT pg_advisory_unlock(hashtext(:lock_key))"),
                        {"lock_key": key},
                    )
                except Exception:
                    # A failed transaction can reject the unlock statement.
                    # Session close still releases a session advisory lock; do
                    # not replace the original acquisition exception.
                    logger.exception(
                        "Explicit advisory unlock failed; connection close "
                        "will release key=%s",
                        key,
                    )
            else:
                async with _sqlite_guard:
                    _sqlite_keys.discard(key)


@asynccontextmanager
async def acquisition_run_locks(
    session: AsyncSession, keys: list[str]
) -> AsyncIterator[tuple[bool, str | None]]:
    """Acquire a stable ordered lock set for multi-connector runs."""
    async with AsyncExitStack() as stack:
        for key in sorted(set(keys)):
            acquired = await stack.enter_async_context(
                acquisition_run_lock(session, key)
            )
            if not acquired:
                yield False, key
                return
        yield True, None
