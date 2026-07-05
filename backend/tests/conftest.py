import asyncio
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

TEST_DB_PATH = Path(__file__).resolve().parent / "test_data" / "test_smart_reporting.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create a fresh event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create an async SQLite engine for testing."""
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
    engine = create_async_engine(db_url, echo=False)

    # Set testing flag so settings don't enforce secrets
    from backend.config import settings
    settings.testing = True
    settings.database_url = db_url

    yield engine
    await engine.dispose()
    # Cleanup test DB
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Yield a fresh async database session for each test."""
    from backend.storage.database import Base
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
