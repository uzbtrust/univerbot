"""
Validation utilities for the bot.
"""
import re
from typing import Optional


def validate_time_format(time_str: str) -> bool:
    """
    Validate time string in HH:MM format.
    
    Args:
        time_str: Time string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    pattern = r"^(?:[01]\d|2[0-3]):[0-5]\d$"
    return bool(re.match(pattern, time_str))


def validate_word_count(text: str, max_words: int = 5) -> tuple[bool, int]:
    """
    Validate word count in text.
    
    Args:
        text: Text to validate
        max_words: Maximum allowed words
        
    Returns:
        tuple: (is_valid, word_count)
    """
    words = text.split()
    word_count = len(words)
    return word_count <= max_words, word_count


def validate_channel_id(channel_id: Optional[int]) -> bool:
    """
    Validate channel ID.
    
    Args:
        channel_id: Channel ID to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return channel_id is not None and isinstance(channel_id, int)
