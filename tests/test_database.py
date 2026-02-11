"""Tests for database operations."""
import pytest
from utils.database import DatabaseManager


@pytest.fixture
def db(test_db_path):
    """Create test database instance."""
    db = DatabaseManager()
    db._db_path = test_db_path
    db._initialized = False
    db.__init__()  # Re-initialize with test path
    yield db


def test_add_user(db):
    """Test adding a user."""
    db.add_user(12345)
    assert db.user_exists(12345) is True


def test_user_not_exists(db):
    """Test user doesn't exist."""
    assert db.user_exists(99999) is False


def test_add_superadmin(db):
    """Test adding superadmin."""
    db.add_superadmin(11111)
    assert db.is_superadmin(11111) is True


def test_is_premium_user_superadmin(db):
    """Test superadmin has premium privileges."""
    db.add_user(22222)
    db.add_superadmin(22222)
    assert db.is_premium_user(22222) is True


def test_add_channel(db):
    """Test adding channel."""
    db.add_user(33333)
    db.add_channel(-1001234567890, 33333, premium=False)
    assert db.channel_exists(-1001234567890, premium=False) is True


def test_count_user_channels(db):
    """Test counting user channels."""
    user_id = 44444
    db.add_user(user_id)
    db.add_channel(-1001111111111, user_id, premium=False)
    db.add_channel(-1002222222222, user_id, premium=False)
    assert db.count_user_channels(user_id, premium=False) == 2


def test_update_channel_post(db):
    """Test updating channel post."""
    user_id = 55555
    channel_id = -1003333333333
    db.add_user(user_id)
    db.add_channel(channel_id, user_id, premium=False)
    db.update_channel_post(channel_id, 1, "09:00", "test theme", premium=False)
    
    channel = db.get_channel_by_id(channel_id, premium=False)
    assert channel[2] == "09:00"  # post1
    assert channel[3] == "test theme"  # theme1


def test_delete_channel(db):
    """Test deleting channel."""
    user_id = 66666
    channel_id = -1004444444444
    db.add_user(user_id)
    db.add_channel(channel_id, user_id, premium=False)
    assert db.channel_exists(channel_id, premium=False) is True
    
    db.delete_channel(channel_id, premium=False)
    assert db.channel_exists(channel_id, premium=False) is False


def test_premium_cache(db):
    """Test premium status caching."""
    user_id = 77777
    db.add_user(user_id)
    db.add_superadmin(user_id)
    
    assert db.is_premium_user(user_id) is True
    
    assert db.is_premium_user(user_id) is True
