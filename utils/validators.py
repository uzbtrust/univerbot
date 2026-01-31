import re
from typing import Optional


def validate_time_format(time_str: str) -> bool:
    pattern = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
    return bool(re.match(pattern, time_str))


def validate_word_count(text: str, max_words: int = 5) -> tuple[bool, int]:
    words = text.split()
    word_count = len(words)
    return word_count <= max_words, word_count


def validate_channel_id(channel_id: Optional[int]) -> bool:
    return channel_id is not None and isinstance(channel_id, int)
