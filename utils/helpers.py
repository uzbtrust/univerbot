"""
Helper utilities for the bot.
"""
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def extract_user_id_from_caption(caption: str) -> Optional[int]:
    """
    Extract user ID from message caption.
    
    Args:
        caption: Message caption containing user ID
        
    Returns:
        Optional[int]: Extracted user ID or None if not found
    """
    try:
        # Extract user ID from caption like "User ID: 123456"
        match = re.search(r"User ID:\s*(\d+)", caption)
        if match:
            return int(match.group(1))
    except (AttributeError, ValueError) as e:
        logger.error(f"Error extracting user ID from caption: {e}")
    return None


def generate_channel_info_text(channel_data: tuple, max_posts: int = 3) -> str:
    """
    Generate formatted channel information text.
    
    Args:
        channel_data: Channel data tuple from database
        max_posts: Maximum number of posts to display
        
    Returns:
        str: Formatted channel information
    """
    if not channel_data or len(channel_data) < 2:
        return "Ma'lumot topilmadi"
    
    text = f"Channel ID: {channel_data[1]}\n"
    
    # Start from index 2 (after user_id and id)
    # Each pair is (time, theme)
    for i in range(max_posts):
        time_idx = 2 + (i * 2)
        theme_idx = 3 + (i * 2)
        
        if time_idx < len(channel_data) and theme_idx < len(channel_data):
            time_val = channel_data[time_idx]
            theme_val = channel_data[theme_idx]
            
            if time_val and theme_val:
                text += f"{time_val} - {theme_val}\n"
    
    return text


def format_payment_message(full_name: str, user_id: int, subscription_type: str) -> str:
    """
    Format payment notification message for admin.
    
    Args:
        full_name: User's full name
        user_id: User's ID
        subscription_type: Type of subscription
        
    Returns:
        str: Formatted message
    """
    return (
        f"Yangi obuna!\n\n"
        f"Foydalanuvchi: {full_name}\n"
        f"User ID: {user_id}\n"
        f"Obuna turi: {subscription_type}"
    )


def get_post_number_from_text(text: str) -> Optional[int]:
    """
    Extract post number from text like "1 marta", "2 marta", etc.
    
    Args:
        text: Text containing post number
        
    Returns:
        Optional[int]: Post number or None if invalid
    """
    try:
        parts = text.split()
        if len(parts) >= 1 and parts[0].isdigit():
            return int(parts[0])
    except (ValueError, AttributeError):
        pass
    return None
