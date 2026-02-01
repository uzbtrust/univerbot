import logging
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot
from aiogram.types import BufferedInputFile

from utils.database import db
from services.grok_service import grok_service
from services.image_service import image_service
from config import TIMEZONE, IMAGE_MODE

logger = logging.getLogger(__name__)


class PostScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False
        self.tz = ZoneInfo(TIMEZONE)
        self.post_queue = asyncio.Queue()
        self.worker_count = 3
        self.workers_started = False

    async def get_all_scheduled_posts(self):
        current_time = datetime.now(self.tz).strftime("%H:%M")
        scheduled_posts = []

        free_channels = db.execute_query(
            """SELECT user_id, id,
                      post1, theme1, post2, theme2, post3, theme3
               FROM channel""",
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

        premium_channels = db.execute_query(
            """SELECT user_id, id,
                      post1, theme1, image1,
                      post2, theme2, image2,
                      post3, theme3, image3,
                      post4, theme4, image4,
                      post5, theme5, image5,
                      post6, theme6, image6,
                      post7, theme7, image7,
                      post8, theme8, image8,
                      post9, theme9, image9,
                      post10, theme10, image10,
                      post11, theme11, image11,
                      post12, theme12, image12,
                      post13, theme13, image13,
                      post14, theme14, image14,
                      post15, theme15, image15
               FROM premium_channel""",
            fetch_all=True
        )

        for channel in premium_channels:
            user_id = channel[0]
            channel_id = channel[1]

            for i in range(1, 16):
                base_idx = 2 + (i - 1) * 3
                post_time_idx = base_idx
                post_theme_idx = base_idx + 1
                post_image_idx = base_idx + 2

                if post_image_idx < len(channel):
                    post_time = channel[post_time_idx]
                    post_theme = channel[post_theme_idx]
                    post_image = channel[post_image_idx] if channel[post_image_idx] else 'no'

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

        logger.info(f"📊 Scheduler check at {current_time}: Found {len(scheduled_posts)} posts "
                    f"(Premium: {sum(1 for p in scheduled_posts if p['is_premium'])}, "
                    f"Free: {sum(1 for p in scheduled_posts if not p['is_premium'])})")

        return scheduled_posts

    async def send_post(self, post_data: dict):
        try:
            channel_id = post_data['channel_id']
            theme = post_data['theme']
            is_premium = post_data['is_premium']
            post_num = post_data['post_num']
            with_image = post_data.get('with_image', False)

            logger.info(f"🔄 Generating post for channel {channel_id} (Premium: {is_premium}, Theme: {theme}, With Image: {with_image})")

            post_text = await grok_service.generate_post(theme, is_premium)

            if not post_text:
                logger.error(f"❌ Failed to generate post text for channel {channel_id}")
                return

            logger.info(f"✍️ Generated post text ({len(post_text)} chars) for channel {channel_id}")

            if with_image and is_premium:
                logger.info(f"🎨 Generating image for premium post...")
                image_bytes = await image_service.generate_image(post_text)

                if image_bytes:
                    photo = BufferedInputFile(image_bytes, filename="post_image.jpg")
                    await self.bot.send_photo(
                        chat_id=channel_id,
                        photo=photo,
                        caption=post_text
                    )
                    logger.info(f"✅ Post with image sent to channel {channel_id}")
                else:
                    await self.bot.send_message(
                        chat_id=channel_id,
                        text=post_text
                    )
                    logger.warning(f"⚠️ Image generation failed, sent text only to {channel_id}")
            else:
                logger.info(f"📤 Sending text post to channel {channel_id}")
                await self.bot.send_message(
                    chat_id=channel_id,
                    text=post_text
                )
                logger.info(f"✅ Text post sent to channel {channel_id}")

            user_type = "Premium" if is_premium else "Free"
            image_status = " (with image)" if (with_image and is_premium) else ""
            logger.info(
                f"✅ Post #{post_num} successfully sent | "
                f"Channel: {channel_id} | "
                f"Type: {user_type}{image_status} | "
                f"Theme: {theme}"
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to send post to channel {post_data['channel_id']}: {e}",
                exc_info=True
            )

    async def process_scheduled_posts(self):
        try:
            posts = await self.get_all_scheduled_posts()

            if posts:
                logger.info(f"📬 Adding {len(posts)} posts to queue (current queue size: {self.post_queue.qsize()})")

                for post in posts:
                    await self.post_queue.put(post)

                logger.info(f"✅ Added {len(posts)} posts to queue")

        except Exception as e:
            logger.error(f"Error processing scheduled posts: {e}", exc_info=True)

    async def worker(self, worker_id: int, stop_event: asyncio.Event):
        logger.info(f"🔧 Worker {worker_id} started")
        while self.running and not stop_event.is_set():
            try:
                post = await asyncio.wait_for(self.post_queue.get(), timeout=1.0)
                await self.send_post(post)
                self.post_queue.task_done()
                await asyncio.sleep(0.5)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
        logger.info(f"🔧 Worker {worker_id} stopped")

    async def run(self, stop_event: asyncio.Event):
        self.running = True
        logger.info("🚀 Post scheduler started")

        for i in range(self.worker_count):
            asyncio.create_task(self.worker(i + 1, stop_event))
        logger.info(f"🔧 Started {self.worker_count} workers")

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
            logger.info(f"⏰ Processing posts for {minute}")
            await self.process_scheduled_posts()
        except Exception as e:
            logger.error(f"Error processing posts for {minute}: {e}", exc_info=True)

    def stop(self):
        self.running = False
        logger.info("🛑 Post scheduler stopped")
