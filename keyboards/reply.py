"""
Reply keyboard layouts for the bot.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import MAX_POSTS_FREE, MAX_POSTS_PREMIUM


def get_channel_button():
    """Generate channel post count keyboard based on MAX_POSTS_FREE."""
    keyboard = []
    for i in range(1, MAX_POSTS_FREE + 1):
        keyboard.append([KeyboardButton(text=f"{i} marta")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_premium_channel_button():
    """Generate premium channel post count keyboard based on MAX_POSTS_PREMIUM."""
    keyboard = []
    row = []
    
    for i in range(1, MAX_POSTS_PREMIUM + 1):
        row.append(KeyboardButton(text=f"{i} marta"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    # Add remaining buttons
    if row:
        keyboard.append(row)
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )


# Create default instances for backward compatibility
channel_button = get_channel_button()
premium_channel_button = get_premium_channel_button()
