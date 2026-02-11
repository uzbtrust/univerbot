import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ENV_FILE_PATH = Path(__file__).parent.parent / ".env"


def read_env_file() -> dict:
    env_vars = {}
    try:
        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except FileNotFoundError:
        logger.error(f".env file not found at {ENV_FILE_PATH}")
    return env_vars


def update_env_value(key: str, new_value: str) -> bool:
    try:
        lines = []
        found = False

        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and '=' in stripped:
                line_key = stripped.split('=', 1)[0].strip()
                if line_key == key:
                    lines[i] = f"{key}={new_value}\n"
                    found = True
                    break

        if not found:
            lines.append(f"\n{key}={new_value}\n")

        with open(ENV_FILE_PATH, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        os.environ[key] = new_value

        logger.info(f"Updated {key} in .env file")
        return True
    except Exception as e:
        logger.error(f"Failed to update {key} in .env: {e}")
        return False


def get_current_settings() -> dict:
    env_vars = read_env_file()
    return {
        'CARD_NUMBER': env_vars.get('CARD_NUMBER', ''),
        'CARD_NAME': env_vars.get('CARD_NAME', ''),
        'CARD_SURNAME': env_vars.get('CARD_SURNAME', ''),
        'WEEKLY_PRICE': env_vars.get('WEEKLY_PRICE', '5000'),
        'DAY15_PRICE': env_vars.get('DAY15_PRICE', '10000'),
        'MONTHLY_PRICE': env_vars.get('MONTHLY_PRICE', '20000'),
        'MAX_POSTS_FREE': env_vars.get('MAX_POSTS_FREE', '3'),
        'MAX_POSTS_PREMIUM': env_vars.get('MAX_POSTS_PREMIUM', '15'),
        'MAX_CHANNELS_FREE': env_vars.get('MAX_CHANNELS_FREE', '1'),
        'MAX_CHANNELS_PREMIUM': env_vars.get('MAX_CHANNELS_PREMIUM', '2'),
        'MAX_THEME_WORDS_FREE': env_vars.get('MAX_THEME_WORDS_FREE', '10'),
        'MAX_THEME_WORDS_PREMIUM': env_vars.get('MAX_THEME_WORDS_PREMIUM', '15'),
        'IMAGE_MODE': env_vars.get('IMAGE_MODE', 'OFF'),
    }
