"""
Pytest configuration and fixtures.
"""
import os
import pytest
import pytest_asyncio
import asyncio

# Test uchun SQLite ishlatamiz (aiosqlite orqali)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_temp.db")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db(tmp_path):
    """Create a fresh async database instance for each test."""
    from utils.database import DatabaseManager
    from sqlalchemy.ext.asyncio import create_async_engine

    db_file = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    manager = DatabaseManager.__new__(DatabaseManager)
    manager._created = True
    manager._db_ready = False
    manager._premium_cache = {}
    manager._cache_ttl_seconds = 300
    manager._cache_max_size = 10000
    manager._engine = create_async_engine(db_url, echo=False)

    await manager.initialize()
    yield manager
    await manager.close_all()
