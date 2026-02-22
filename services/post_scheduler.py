import logging
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramRetryAfter
from aiolimiter import AsyncLimiter

from utils.database import db
from services.grok_service import grok_service
from services.image_service import image_service
from config import (
    TIMEZONE, TELEGRAM_RATE_LIMIT,
    SCHEDULER_MIN_WORKERS, SCHEDULER_MAX_WORKERS, SCHEDULER_SCALE_THRESHOLD
)

logger = logging.getLogger(__name__)
telegram_limiter = AsyncLimiter(max_rate=TELEGRAM_RATE_LIMIT, time_period=1)


class PostScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False
        self.tz = ZoneInfo(TIMEZONE)
        self.post_queue = asyncio.PriorityQueue()
        self.min_workers = SCHEDULER_MIN_WORKERS
        self.max_workers = SCHEDULER_MAX_WORKERS
        self.scale_threshold = SCHEDULER_SCALE_THRESHOLD
        self.active_workers = 0
        self.worker_tasks: list[asyncio.Task] = []
        self.post_counter = 0
        self._worker_lock = asyncio.Lock()
        self._stop_event = None

    async def get_all_scheduled_posts(self):
        current_time = datetime.now(self.tz).strftime("%H:%M")
        scheduled_posts = []

        # Free kanallar — SQL da filter
        free_channels = db.execute_query(
            """SELECT user_id, id,
                      post1, theme1, post2, theme2, post3, theme3
               FROM channel
               WHERE post1 = ? OR post2 = ? OR post3 = ?""",
            (current_time, current_time, current_time),
            fetch_all=True
        )

        for channel in free_channels:
            user_id = channel[0]
            channel_id = channel[1]

            for i in range(1, 4):
                post_time_idx = 2 + (i - 1) * 2
                post_theme_idx = 3 + (i - 1) * 2

                if post_time_idx < len(channel) and post_theme_idx < len(channel):
                    post_time = channel[post_time_idx]
                    post_theme = channel[post_theme_idx]

                    if post_time and post_theme and post_time == current_time:
                        scheduled_posts.append({
                            'channel_id': channel_id,
                            'user_id': user_id,
                            'theme': post_theme,
                            'post_num': i,
                            'is_premium': False,
                            'with_image': False,
                            'priority': 1
                        })

        # Premium kanallar — SQL da filter (15 ta post)
        premium_where = " OR ".join([f"post{i} = ?" for i in range(1, 16)])
        premium_params = tuple([current_time] * 15)

        premium_channels = db.execute_query(
            f"""SELECT user_id, id,
                      post1, theme1, post2, theme2, post3, theme3,
                      post4, theme4, post5, theme5, post6, theme6,
                      post7, theme7, post8, theme8, post9, theme9,
                      post10, theme10, post11, theme11, post12, theme12,
                      post13, theme13, post14, theme14, post15, theme15,
                      image1, image2, image3, image4, image5,
                      image6, image7, image8, image9, image10,
                      image11, image12, image13, image14, image15
               FROM premium_channel
               WHERE {premium_where}""",
            premium_params,
            fetch_all=True
        )

        for channel in premium_channels:
            user_id = channel[0]
            channel_id = channel[1]

            for i in range(1, 16):
                post_time_idx = 2 + (i - 1) * 2
                post_theme_idx = post_time_idx + 1
                post_image_idx = 32 + (i - 1)

                if post_theme_idx < len(channel):
                    post_time = channel[post_time_idx]
                    post_theme = channel[post_theme_idx]
                    post_image = channel[post_image_idx] if post_image_idx < len(channel) and channel[post_image_idx] else 'no'

                    if post_time and post_theme and post_time == current_time:
                        scheduled_posts.append({
                            'channel_id': channel_id,
                            'user_id': user_id,
                            'theme': post_theme,
                            'post_num': i,
                            'is_premium': True,
                            'with_image': post_image == 'yes',
                            'priority': 0
                        })

        scheduled_posts.sort(key=lambda x: x['priority'])

        if scheduled_posts:
            logger.info(f"📊 {current_time}: {len(scheduled_posts)} post topildi "
                        f"(Premium: {sum(1 for p in scheduled_posts if p['is_premium'])}, "
                        f"Free: {sum(1 for p in scheduled_posts if not p['is_premium'])})")

        return scheduled_posts

    async def send_post(self, post_data: dict):
        channel_id = post_data['channel_id']
        theme = post_data['theme']
        is_premium = post_data['is_premium']
        post_num = post_data['post_num']
        with_image = post_data.get('with_image', False)

        try:
            post_text = await grok_service.generate_post(theme, is_premium)

            if not post_text:
                logger.error(f"❌ Post text yaratib bo'lmadi: channel={channel_id}")
                return

            sent = False

            # Rasmli post yuborish (xato bo'lsa matn yuboriladi)
            if with_image and is_premium:
                try:
                    image_bytes = await image_service.generate_image(post_text)
                    if image_bytes:
                        filename = "post_image.png" if image_bytes[:8] == b'\x89PNG\r\n\x1a\n' else "post_image.jpg"
                        photo = BufferedInputFile(image_bytes, filename=filename)
                        caption = post_text[:1024] if len(post_text) > 1024 else post_text
                        async with telegram_limiter:
                            await self.bot.send_photo(
                                chat_id=channel_id,
                                photo=photo,
                                caption=caption,
                                parse_mode="HTML"
                            )
                        sent = True
                        logger.info(f"✅ Rasmli post yuborildi: channel={channel_id}")
                except Exception as img_err:
                    logger.warning(f"⚠️ send_photo xato, matn yuboriladi: channel={channel_id}: {img_err}")

            # Matnli post (fallback yoki oddiy post)
            if not sent:
                await self._send_text_with_retry(channel_id, post_text)

            logger.info(f"✅ Post #{post_num} | Channel: {channel_id} | "
                        f"{'Premium' if is_premium else 'Free'} | Theme: {theme[:30]}")

        except Exception as e:
            logger.error(f"❌ Post yuborib bo'lmadi: channel={channel_id}: {e}", exc_info=True)

    async def _send_text_with_retry(self, channel_id: int, text: str, max_retries: int = 2):
        """Matnli xabar yuborish + Telegram rate limit uchun retry."""
        for attempt in range(max_retries + 1):
            try:
                async with telegram_limiter:
                    await self.bot.send_message(
                        chat_id=channel_id,
                        text=text,
                        parse_mode="HTML"
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

    async def _adjust_workers(self):
        """Queue hajmiga qarab workerlar sonini oshirish."""
        queue_size = self.post_queue.qsize()
        desired = min(
            self.max_workers,
            max(self.min_workers, queue_size // self.scale_threshold + 1)
        )

        async with self._worker_lock:
            if desired > self.active_workers:
                for i in range(self.active_workers, desired):
                    task = asyncio.create_task(self.worker(i + 1, self._stop_event))
                    self.worker_tasks.append(task)
                    self.active_workers += 1
                logger.info(f"⬆️ Workers: {self.active_workers} (queue: {queue_size})")

    async def process_scheduled_posts(self):
        try:
            posts = await self.get_all_scheduled_posts()

            if posts:
                for post in posts:
                    self.post_counter += 1
                    priority = (post['priority'], self.post_counter, post)
                    await self.post_queue.put(priority)

                # Kerak bo'lsa qo'shimcha worker qo'shish
                await self._adjust_workers()

        except Exception as e:
            logger.error(f"Error processing scheduled posts: {e}", exc_info=True)

    async def worker(self, worker_id: int, stop_event: asyncio.Event):
        logger.info(f"🔧 Worker {worker_id} started")
        idle_cycles = 0
        try:
            while self.running and not stop_event.is_set():
                try:
                    priority_item = await asyncio.wait_for(self.post_queue.get(), timeout=1.0)
                    idle_cycles = 0
                    priority, counter, post = priority_item
                    await self.send_post(post)
                    self.post_queue.task_done()
                    await asyncio.sleep(0.5)
                except asyncio.TimeoutError:
                    idle_cycles += 1
                    # Qo'shimcha workerlar 30s idle bo'lsa o'chadi
                    if idle_cycles > 30 and worker_id > self.min_workers:
                        break
                    continue
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
        finally:
            async with self._worker_lock:
                self.active_workers = max(0, self.active_workers - 1)
            logger.info(f"🔧 Worker {worker_id} stopped (active: {self.active_workers})")

    async def run(self, stop_event: asyncio.Event):
        self.running = True
        self._stop_event = stop_event
        logger.info("🚀 Post scheduler started")

        # Boshlang'ich workerlarni ishga tushirish
        for i in range(self.min_workers):
            task = asyncio.create_task(self.worker(i + 1, stop_event))
            self.worker_tasks.append(task)
        self.active_workers = self.min_workers
        logger.info(f"🔧 Started {self.min_workers} workers (max: {self.max_workers})")

        now = datetime.now(self.tz)
        initial_sleep = 60 - now.second
        await asyncio.sleep(initial_sleep)

        last_processed_minute = None

        while self.running and not stop_event.is_set():
            current_minute = datetime.now(self.tz).strftime("%H:%M")

            if current_minute != last_processed_minute:
                last_processed_minute = current_minute
                asyncio.create_task(self._safe_process_posts(current_minute))

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=1)
            except asyncio.TimeoutError:
                pass

    async def _safe_process_posts(self, minute: str):
        try:
            await self.process_scheduled_posts()
        except Exception as e:
            logger.error(f"Error processing posts for {minute}: {e}", exc_info=True)

    def stop(self):
        self.running = False
        logger.info("🛑 Post scheduler stopped")
