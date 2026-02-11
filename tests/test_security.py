"""Tests for security utilities."""
import pytest
from utils.security import (
    check_rate_limit,
    sanitize_channel_id,
    validate_broadcast_message,
    sanitize_text_input,
    validate_theme,
    validate_time_format,
)


def test_rate_limit_within_bounds():
    """Test rate limiting allows normal usage."""
    user_id = 12345
    for _ in range(20):
        assert check_rate_limit(user_id) is True


def test_rate_limit_exceeds():
    """Test rate limiting blocks excessive usage."""
    user_id = 99999
    for _ in range(20):
        check_rate_limit(user_id)
    assert check_rate_limit(user_id) is False


def test_sanitize_channel_id_valid():
    """Test valid channel ID sanitization."""
    assert sanitize_channel_id(-1001234567890) == -1001234567890
    assert sanitize_channel_id("-1001234567890") == -1001234567890


def test_sanitize_channel_id_invalid():
    """Test invalid channel ID rejection."""
    assert sanitize_channel_id(12345) is None
    assert sanitize_channel_id(-999) is None
    assert sanitize_channel_id("invalid") is None


def test_validate_broadcast_message_valid():
    """Test valid broadcast message."""
    is_valid, _ = validate_broadcast_message("Hello users!")
    assert is_valid is True


def test_validate_broadcast_message_empty():
    """Test empty broadcast message rejection."""
    is_valid, msg = validate_broadcast_message("")
    assert is_valid is False
    assert "bo'sh" in msg.lower()


def test_validate_broadcast_message_too_long():
    """Test oversized broadcast message rejection."""
    long_msg = "x" * 5000
    is_valid, msg = validate_broadcast_message(long_msg)
    assert is_valid is False


def test_sanitize_text_input():
    """Test text input sanitization."""
    assert sanitize_text_input("  hello  ") == "hello"
    assert sanitize_text_input("x" * 600, max_length=500) == "x" * 500


def test_validate_theme_valid():
    """Test valid theme validation."""
    is_valid, _ = validate_theme("salom dunyo")
    assert is_valid is True


def test_validate_theme_too_long():
    """Test theme with too many words."""
    is_valid, msg = validate_theme("bir ikki uch tort besh olti", max_words=5)
    assert is_valid is False


def test_validate_time_format_valid():
    """Test valid time format."""
    assert validate_time_format("09:30") is True
    assert validate_time_format("23:59") is True
    assert validate_time_format("00:00") is True


def test_validate_time_format_invalid():
    """Test invalid time format."""
    assert validate_time_format("25:00") is False
    assert validate_time_format("12:60") is False
    assert validate_time_format("9:30") is False  # Must be 09:30
    assert validate_time_format("invalid") is False
