"""Tests for 24-hour post time edit restriction."""
import pytest


@pytest.mark.asyncio
async def test_time_edit_restriction_free(db):
    user_id = 10101
    channel_id = -1009990001111
    await db.add_user(user_id)
    await db.add_channel(channel_id, user_id, premium=False)

    await db.update_channel_post(channel_id, 1, "09:00", "theme", premium=False)

    await db.update_single_post(channel_id, 1, theme="new theme", premium=False)

    with pytest.raises(ValueError):
        await db.update_single_post(channel_id, 1, time="10:00", premium=False)


@pytest.mark.asyncio
async def test_time_edit_restriction_premium(db):
    user_id = 20202
    channel_id = -1009990002222
    await db.add_user(user_id)
    await db.add_channel(channel_id, user_id, premium=True)

    await db.update_channel_post(channel_id, 1, "08:30", "premium theme", premium=True, with_image='yes')

    await db.update_single_post(channel_id, 1, theme="updated premium theme", premium=True)

    with pytest.raises(ValueError):
        await db.update_single_post(channel_id, 1, time="09:45", premium=True)
