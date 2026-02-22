"""Tests for async database operations."""
import pytest


@pytest.mark.asyncio
async def test_add_user(db):
    """Test adding a user."""
    await db.add_user(12345)
    assert await db.user_exists(12345) is True


@pytest.mark.asyncio
async def test_user_not_exists(db):
    """Test user doesn't exist."""
    assert await db.user_exists(99999) is False


@pytest.mark.asyncio
async def test_add_superadmin(db):
    """Test adding superadmin."""
    await db.add_superadmin(11111)
    assert await db.is_superadmin(11111) is True


@pytest.mark.asyncio
async def test_is_premium_user_superadmin(db):
    """Test superadmin has premium privileges."""
    await db.add_user(22222)
    await db.add_superadmin(22222)
    assert await db.is_premium_user(22222) is True


@pytest.mark.asyncio
async def test_add_channel(db):
    """Test adding channel."""
    await db.add_user(33333)
    await db.add_channel(-1001234567890, 33333, premium=False)
    assert await db.channel_exists(-1001234567890, premium=False) is True


@pytest.mark.asyncio
async def test_count_user_channels(db):
    """Test counting user channels."""
    user_id = 44444
    await db.add_user(user_id)
    await db.add_channel(-1001111111111, user_id, premium=False)
    await db.add_channel(-1002222222222, user_id, premium=False)
    assert await db.count_user_channels(user_id, premium=False) == 2


@pytest.mark.asyncio
async def test_update_channel_post(db):
    """Test updating channel post."""
    user_id = 55555
    channel_id = -1003333333333
    await db.add_user(user_id)
    await db.add_channel(channel_id, user_id, premium=False)
    await db.update_channel_post(channel_id, 1, "09:00", "test theme", premium=False)

    channel = await db.get_channel_by_id(channel_id, premium=False)
    assert channel[2] == "09:00"  # post1
    assert channel[3] == "test theme"  # theme1


@pytest.mark.asyncio
async def test_delete_channel(db):
    """Test deleting channel."""
    user_id = 66666
    channel_id = -1004444444444
    await db.add_user(user_id)
    await db.add_channel(channel_id, user_id, premium=False)
    assert await db.channel_exists(channel_id, premium=False) is True

    await db.delete_channel(channel_id, premium=False)
    assert await db.channel_exists(channel_id, premium=False) is False


@pytest.mark.asyncio
async def test_premium_cache(db):
    """Test premium status caching."""
    user_id = 77777
    await db.add_user(user_id)
    await db.add_superadmin(user_id)

    assert await db.is_premium_user(user_id) is True

    assert await db.is_premium_user(user_id) is True
