"""Test fixtures and utilities."""

import os

# Set required env vars BEFORE importing app code (some read at import time)
os.environ.setdefault("API_KEY_MASTER_KEY", "test-master-key-32bytes-long!!!")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32bytes-long!!!")

from collections.abc import AsyncIterator
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import Base, get_db
from app.main import app

# Allow override via env var; default to in-memory SQLite for fast tests
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine and tables."""
    engine = create_async_engine(
        TEST_DATABASE_URL, echo=False, poolclass=NullPool, pool_pre_ping=True
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test (auto-rollback + cleanup)."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
        # Clean up committed test data so tests don't leak
        from app.models.config import LLMProviderConfig, SystemSetting
        await session.execute(delete(SystemSetting))
        await session.execute(delete(LLMProviderConfig))
        await session.commit()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Create an async test client with overridden DB dependency."""
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
