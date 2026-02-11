"""
Pytest configuration and fixtures.
"""
import pytest
import asyncio
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db_path(tmp_path: Path) -> str:
    """Provide temporary database path for tests."""
    return str(tmp_path / "test.db")
