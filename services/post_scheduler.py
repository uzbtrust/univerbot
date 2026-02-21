import logging
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from utils.database import db
from services.tasks import send_post_task
from config import TIMEZONE

logger = logging.getLogger(__name__)


class PostScheduler:
    def __init__(self):
        self.running = False
        self.tz = ZoneInfo(TIMEZONE)

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

    async def process_scheduled_posts(self):
        """Postlarni olish va taskiq queue ga yuborish."""
        try:
            posts = await self.get_all_scheduled_posts()

            if posts:
                for post in posts:
                    await send_post_task.kiq(
                        channel_id=post['channel_id'],
                        theme=post['theme'],
                        is_premium=post['is_premium'],
                        post_num=post['post_num'],
                        with_image=post.get('with_image', False),
                    )
                logger.info(f"📤 {len(posts)} task Redis queue ga yuborildi")

        except Exception as e:
            logger.error(f"Error processing scheduled posts: {e}", exc_info=True)

    async def run(self, stop_event: asyncio.Event):
        self.running = True
        logger.info("🚀 Post scheduler started (taskiq mode)")

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
