"""Test fixtures — isolated SQLite DB, async client, auth helper."""

import asyncio
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force test env before app imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "testpass123"
os.environ["DEBUG"] = "false"

from app.auth import create_access_token, hash_password
from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import User

get_settings.cache_clear()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Seed admin
    async with factory() as session:
        session.add(
            User(email="admin@test.local", hashed_password=hash_password("testpass123"))
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    token = create_access_token(data={"sub": "admin@test.local"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_prospect_payload() -> dict:
    return {
        "company_name": "Béton Atlas SAS",
        "sector": "Construction",
        "company_size": "11-50",
        "signal_type": "BOAMP_WIN",
        "signal_details": "Won multiple lots in Casablanca corridor",
        "decision_maker_name": "Marie Dupont",
        "decision_maker_title": "Fondateur",
        "email": "marie@beton-atlas.fr",
        "data_source": "BOAMP public tender search",
        "informed_at": datetime.now(timezone.utc).isoformat(),
        "source": "BOAMP",
        "notes": "Pilot prospect",
    }
