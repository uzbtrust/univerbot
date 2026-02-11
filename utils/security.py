from __future__ import annotations
import time
import re
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

_rate_limit_store: Dict[int, Tuple[float, int]] = {}
_RATE_WINDOW = 60
_MAX_ACTIONS_PER_WINDOW = 20


def check_rate_limit(user_id: int) -> bool:
    now = time.time()
    last_time, count = _rate_limit_store.get(user_id, (now, 0))

    if now - last_time > _RATE_WINDOW:
        _rate_limit_store[user_id] = (now, 1)
        return True

    if count >= _MAX_ACTIONS_PER_WINDOW:
        logger.warning(f"Rate limit exceeded for user {user_id}")
        return False

    _rate_limit_store[user_id] = (last_time, count + 1)
    return True


def sanitize_channel_id(channel_id: int | str) -> int | None:
    try:
        cid = int(channel_id)
        if -10000000000000 < cid < -1000000000:
            return cid
        logger.warning(f"Invalid channel ID range: {cid}")
        return None
    except (ValueError, TypeError):
        logger.warning(f"Invalid channel ID format: {channel_id}")
        return None


def validate_broadcast_message(message_text: str, max_length: int = 4096) -> tuple[bool, str]:
    if not message_text or not message_text.strip():
        return False, "Xabar bo'sh bo'lishi mumkin emas"

    if len(message_text) > max_length:
        return False, f"Xabar {max_length} belgidan oshmasligi kerak"

    return True, ""


def sanitize_text_input(text: str, max_length: int = 500) -> str:
    if not text:
        return ""

    text = text.strip()

    if len(text) > max_length:
        text = text[:max_length]

    return text


def validate_theme(theme: str, max_words: int = 5) -> tuple[bool, str]:
    if not theme or not theme.strip():
        return False, "Mavzu bo'sh bo'lishi mumkin emas"

    words = theme.strip().split()
    if len(words) > max_words:
        return False, f"Mavzu {max_words} so'zdan oshmasligi kerak"

    return True, ""


def validate_time_format(time_str: str) -> bool:
    if not time_str:
        return False

    pattern = r'^([01]\d|2[0-3]):([0-5]\d)$'
    return bool(re.match(pattern, time_str.strip()))


__all__ = [
    "check_rate_limit",
    "sanitize_channel_id",
    "validate_broadcast_message",
    "sanitize_text_input",
    "validate_theme",
    "validate_time_format",
]
