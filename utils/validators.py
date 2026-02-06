import re
from typing import Optional


def validate_time_format(time_str: str) -> bool:
    """
    Vaqt formatini tekshirish (HH:MM)
    00:00 dan 23:59 gacha qabul qilinadi
    """
    if not time_str or not isinstance(time_str, str):
        return False

    pattern = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
    return bool(re.match(pattern, time_str.strip()))


def validate_word_count(text: str, max_words: int = 5) -> tuple[bool, int]:
    """So'z sonini tekshirish"""
    if not text or not isinstance(text, str):
        return False, 0

    words = text.strip().split()
    word_count = len(words)
    return word_count <= max_words, word_count


def validate_channel_id(channel_id: Optional[int]) -> bool:
    return channel_id is not None and isinstance(channel_id, int)
