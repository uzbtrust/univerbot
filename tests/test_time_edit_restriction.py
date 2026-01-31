"""Tests for 24-hour post time edit restriction."""
import pytest
from utils.database import DatabaseManager


@pytest.fixture
def db(test_db_path):
    db = DatabaseManager()
    db._db_path = test_db_path
    db._initialized = False
    db.__init__()
    yield db


def test_time_edit_restriction_free(db):
    user_id = 10101
    channel_id = -1009990001111
    db.add_user(user_id)
    db.add_channel(channel_id, user_id, premium=False)

    # Initial set should work
    db.update_channel_post(channel_id, 1, "09:00", "theme", premium=False)

    # Theme-only change should be allowed inside 24h
    db.update_single_post(channel_id, 1, theme="new theme", premium=False)

    # Time change inside 24h should be blocked
    with pytest.raises(ValueError):
        db.update_single_post(channel_id, 1, time="10:00", premium=False)


def test_time_edit_restriction_premium(db):
    user_id = 20202
    channel_id = -1009990002222
    db.add_user(user_id)
    db.add_channel(channel_id, user_id, premium=True)

    # Initial set should work (with image preference)
    db.update_channel_post(channel_id, 1, "08:30", "premium theme", premium=True, with_image='yes')

    # Theme-only change should be allowed
    db.update_single_post(channel_id, 1, theme="updated premium theme", premium=True)

    # Time change inside 24h should be blocked
    with pytest.raises(ValueError):
        db.update_single_post(channel_id, 1, time="09:45", premium=True)
