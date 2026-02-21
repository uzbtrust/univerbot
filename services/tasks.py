import logging
import asyncio
from taskiq_redis import ListQueueBroker
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramRetryAfter
from aiolimiter import AsyncLimiter
from config import REDIS_URL, BOT_TOKEN, TELEGRAM_RATE_LIMIT

logger = logging.getLogger(__name__)

broker = ListQueueBroker(REDIS_URL)
telegram_limiter = AsyncLimiter(max_rate=TELEGRAM_RATE_LIMIT, time_period=1)

# Bot instance — main.py dan set_bot() orqali yoki worker startup da yaratiladi
_bot_instance = None


def set_bot(bot):
    """Main process dan bot instance ni set qilish."""
    global _bot_instance
    _bot_instance = bot


def get_bot():
    """Joriy bot instance ni olish."""
    global _bot_instance
    if _bot_instance is None:
        from aiogram import Bot
        _bot_instance = Bot(token=BOT_TOKEN)
    return _bot_instance


@broker.on_event("startup")
async def on_startup(state):
    """Worker process startup."""
    get_bot()
    logger.info("Taskiq broker started")


@broker.on_event("shutdown")
async def on_shutdown(state):
    """Worker process shutdown."""
    global _bot_instance
    if _bot_instance:
        await _bot_instance.session.close()
        _bot_instance = None
    logger.info("Taskiq broker stopped")


@broker.task
async def send_post_task(
    channel_id: int,
    theme: str,
    is_premium: bool,
    post_num: int,
    with_image: bool,
):
    """Post yuborish task — taskiq orqali bajariladi."""
    from services.grok_service import grok_service
    from services.image_service import image_service

    bot = get_bot()

    try:
        post_text = await grok_service.generate_post(theme, is_premium)
        if not post_text:
            logger.error(f"Post text yaratib bo'lmadi: channel={channel_id}")
            return

        sent = False

        if with_image and is_premium:
            try:
                image_bytes = await image_service.generate_image(post_text)
                if image_bytes:
                    filename = "post_image.png" if image_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "post_image.jpg"
                    photo = BufferedInputFile(image_bytes, filename=filename)
                    caption = post_text[:1024]
                    async with telegram_limiter:
                        await bot.send_photo(
                            chat_id=channel_id, photo=photo,
                            caption=caption, parse_mode="HTML"
                        )
                    sent = True
                    logger.info(f"✅ Rasmli post: channel={channel_id}")
            except Exception as img_err:
                logger.warning(f"send_photo xato, matn yuboriladi: channel={channel_id}: {img_err}")

        if not sent:
            await _send_text_with_retry(bot, channel_id, post_text)

        logger.info(f"✅ Post #{post_num} | Channel: {channel_id} | "
                    f"{'Premium' if is_premium else 'Free'} | Theme: {theme[:30]}")

    except Exception as e:
        logger.error(f"❌ send_post_task: channel={channel_id}: {e}", exc_info=True)


async def _send_text_with_retry(bot, channel_id: int, text: str, max_retries: int = 2):
    """Matnli xabar yuborish + Telegram rate limit uchun retry."""
    for attempt in range(max_retries + 1):
        try:
            async with telegram_limiter:
                await bot.send_message(
                    chat_id=channel_id, text=text, parse_mode="HTML"
                )
            return
        except TelegramRetryAfter as e:
            logger.warning(f"Rate limit {e.retry_after}s, retry {attempt + 1}: channel={channel_id}")
            await asyncio.sleep(e.retry_after + 0.5)
        except Exception as e:
            logger.error(f"send_message xato: channel={channel_id}: {e}")
            if attempt < max_retries:
                await asyncio.sleep(1)
            else:
                raise
