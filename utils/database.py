"""Async PostgreSQL database manager (asyncpg + SQLAlchemy)."""

import time
import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Tuple

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import DATABASE_URL

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Asia/Tashkent")
ALLOWED_TABLES = {"channel", "premium_channel"}


class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _premium_cache: Dict[int, Tuple[bool, float]] = {}
    _cache_ttl_seconds: int = 300
    _cache_max_size: int = 10000

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._created = False
        return cls._instance

    def __init__(self):
        if self._created:
            return
        self._created = True
        self._db_ready = False

        # postgresql:// → postgresql+asyncpg://
        url = DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self._engine = create_async_engine(
            url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_timeout=30,
        )

    async def initialize(self):
        """Jadvallarni yaratish — on_startup da chaqiriladi."""
        if self._db_ready:
            return

        async with self._engine.begin() as conn:
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS superadmins (
                    id BIGINT PRIMARY KEY
                )
            '''))
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    subscription BOOLEAN DEFAULT FALSE,
                    premium_type TEXT,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP
                )
            '''))
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS channel (
                    user_id BIGINT,
                    id BIGINT PRIMARY KEY,
                    post1 TEXT, theme1 TEXT,
                    post2 TEXT, theme2 TEXT,
                    post3 TEXT, theme3 TEXT,
                    with_image BOOLEAN DEFAULT FALSE,
                    last_edit_time TIMESTAMP
                )
            '''))
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS premium_channel (
                    user_id BIGINT,
                    id BIGINT PRIMARY KEY,
                    post1 TEXT, theme1 TEXT,
                    post2 TEXT, theme2 TEXT,
                    post3 TEXT, theme3 TEXT,
                    post4 TEXT, theme4 TEXT,
                    post5 TEXT, theme5 TEXT,
                    post6 TEXT, theme6 TEXT,
                    post7 TEXT, theme7 TEXT,
                    post8 TEXT, theme8 TEXT,
                    post9 TEXT, theme9 TEXT,
                    post10 TEXT, theme10 TEXT,
                    post11 TEXT, theme11 TEXT,
                    post12 TEXT, theme12 TEXT,
                    post13 TEXT, theme13 TEXT,
                    post14 TEXT, theme14 TEXT,
                    post15 TEXT, theme15 TEXT,
                    with_image BOOLEAN DEFAULT FALSE,
                    last_edit_time TIMESTAMP,
                    image1 TEXT DEFAULT 'no', image2 TEXT DEFAULT 'no',
                    image3 TEXT DEFAULT 'no', image4 TEXT DEFAULT 'no',
                    image5 TEXT DEFAULT 'no', image6 TEXT DEFAULT 'no',
                    image7 TEXT DEFAULT 'no', image8 TEXT DEFAULT 'no',
                    image9 TEXT DEFAULT 'no', image10 TEXT DEFAULT 'no',
                    image11 TEXT DEFAULT 'no', image12 TEXT DEFAULT 'no',
                    image13 TEXT DEFAULT 'no', image14 TEXT DEFAULT 'no',
                    image15 TEXT DEFAULT 'no'
                )
            '''))
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY,
                    referrer_id BIGINT NOT NULL,
                    referred_id BIGINT NOT NULL UNIQUE,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activated BOOLEAN DEFAULT FALSE,
                    activated_at TIMESTAMP
                )
            '''))
            await conn.execute(text('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_users INTEGER DEFAULT 0,
                    premium_users INTEGER DEFAULT 0,
                    total_channels INTEGER DEFAULT 0,
                    total_posts INTEGER DEFAULT 0,
                    posts_with_image INTEGER DEFAULT 0
                )
            '''))

            # Indexes
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_sub ON users(subscription)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_channel_uid ON channel(user_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pchannel_uid ON premium_channel(user_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ref_referrer ON referrals(referrer_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ref_activated ON referrals(referrer_id, activated)"))

            for i in range(1, 4):
                await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_ch_post{i} ON channel(post{i})"))
            for i in range(1, 16):
                await conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_pch_post{i} ON premium_channel(post{i})"))

            # Ustunlarni qo'shish (mavjud bo'lsa e'tiborsiz)
            alter_stmts = [
                "ALTER TABLE channel ADD COLUMN IF NOT EXISTS with_image BOOLEAN DEFAULT FALSE",
                "ALTER TABLE premium_channel ADD COLUMN IF NOT EXISTS with_image BOOLEAN DEFAULT FALSE",
                "ALTER TABLE channel ADD COLUMN IF NOT EXISTS last_edit_time TIMESTAMP",
                "ALTER TABLE premium_channel ADD COLUMN IF NOT EXISTS last_edit_time TIMESTAMP",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_base_date TIMESTAMP",
            ]
            for i in range(1, 16):
                alter_stmts.append(f"ALTER TABLE premium_channel ADD COLUMN IF NOT EXISTS image{i} TEXT DEFAULT 'no'")

            for stmt in alter_stmts:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    pass  # Ustun allaqachon mavjud (SQLite uchun)

        self._db_ready = True
        logger.info("Database initialized (PostgreSQL + asyncpg)")

    async def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
        if not self._db_ready:
            await self.initialize()

        async with self._engine.connect() as conn:
            sa_query = query
            sa_params = {}
            for i, val in enumerate(params):
                sa_query = sa_query.replace("?", f":p{i}", 1)
                sa_params[f"p{i}"] = val

            result = await conn.execute(text(sa_query), sa_params)

            if fetch_one:
                row = result.fetchone()
                return tuple(row) if row else None
            elif fetch_all:
                rows = result.fetchall()
                return [tuple(r) for r in rows]

            await conn.commit()
            return None

    async def close_all(self):
        await self._engine.dispose()
        logger.info("Database engine disposed")

    # ============== User Methods ==============

    async def user_exists(self, user_id: int) -> bool:
        result = await self.execute_query("SELECT 1 FROM users WHERE id = ?", (user_id,), fetch_one=True)
        return result is not None

    def _cleanup_cache_if_needed(self):
        if len(self._premium_cache) > self._cache_max_size:
            now = time.time()
            expired_keys = [k for k, v in self._premium_cache.items() if now - v[1] >= self._cache_ttl_seconds]
            for k in expired_keys:
                del self._premium_cache[k]
            if len(self._premium_cache) > self._cache_max_size:
                sorted_items = sorted(self._premium_cache.items(), key=lambda x: x[1][1])
                keys_to_remove = [k for k, _ in sorted_items[:len(sorted_items) // 2]]
                for k in keys_to_remove:
                    del self._premium_cache[k]

    async def is_premium_user(self, user_id: int) -> bool:
        now = time.time()
        cached = self._premium_cache.get(user_id)
        if cached and now - cached[1] < self._cache_ttl_seconds:
            return cached[0]
        if await self.is_superadmin(user_id):
            self._premium_cache[user_id] = (True, now)
            self._cleanup_cache_if_needed()
            return True
        result = await self.execute_query("SELECT subscription FROM users WHERE id = ?", (user_id,), fetch_one=True)
        is_premium = bool(result and result[0])
        self._premium_cache[user_id] = (is_premium, now)
        self._cleanup_cache_if_needed()
        return is_premium

    async def is_superadmin(self, user_id: int) -> bool:
        result = await self.execute_query("SELECT 1 FROM superadmins WHERE id = ?", (user_id,), fetch_one=True)
        return result is not None

    async def add_user(self, user_id: int, subscription: bool = False):
        await self.execute_query(
            "INSERT INTO users (id, subscription) VALUES (?, ?) ON CONFLICT (id) DO NOTHING",
            (user_id, subscription)
        )

    async def add_superadmin(self, user_id: int):
        await self.execute_query(
            "INSERT INTO superadmins (id) VALUES (?) ON CONFLICT (id) DO NOTHING",
            (user_id,)
        )

    async def update_user_subscription(self, user_id: int, subscription: bool, premium_type: Optional[str] = None):
        if premium_type:
            await self.execute_query("UPDATE users SET subscription = ?, premium_type = ? WHERE id = ?", (subscription, premium_type, user_id))
        else:
            await self.execute_query("UPDATE users SET subscription = ? WHERE id = ?", (subscription, user_id))
        if user_id in self._premium_cache:
            del self._premium_cache[user_id]

    # ============== Channel Methods ==============

    def _get_table_name(self, premium: bool) -> str:
        return "premium_channel" if premium else "channel"

    async def get_user_channels(self, user_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        return await self.execute_query(f"SELECT * FROM {table} WHERE user_id = ?", (user_id,), fetch_all=True)

    async def channel_exists(self, channel_id: int, premium: bool = False) -> bool:
        table = self._get_table_name(premium)
        result = await self.execute_query(f"SELECT 1 FROM {table} WHERE id = ?", (channel_id,), fetch_one=True)
        return result is not None

    async def add_channel(self, channel_id: int, user_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        await self.execute_query(f"INSERT INTO {table} (id, user_id) VALUES (?, ?)", (channel_id, user_id))

    async def _check_24h_restriction(self, channel_id: int, premium: bool):
        last_edit = await self.get_last_edit_time(channel_id, premium=premium)
        if last_edit:
            try:
                last_dt = datetime.fromisoformat(last_edit)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=TZ)
            except ValueError:
                last_dt = None
            if last_dt and datetime.now(TZ) - last_dt < timedelta(hours=24):
                raise ValueError("Post vaqtini faqat 24 soatdan keyin o'zgartirish mumkin.")

    async def update_channel_post(self, channel_id: int, post_num: int, time: str, theme: str, premium: bool = False, with_image: str = 'no', skip_24h_check: bool = False):
        table = self._get_table_name(premium)
        try:
            if not skip_24h_check:
                await self._check_24h_restriction(channel_id, premium)
            if premium:
                await self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ?, image{post_num} = ? WHERE id = ?", (time, theme, with_image, channel_id))
            else:
                await self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ? WHERE id = ?", (time, theme, channel_id))
            if not skip_24h_check:
                await self.update_last_edit_time(channel_id, datetime.now(TZ).isoformat(), premium=premium)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update channel post {post_num} for {channel_id}: {e}")
            raise

    async def get_channel_by_id(self, channel_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        return await self.execute_query(f"SELECT * FROM {table} WHERE id = ?", (channel_id,), fetch_one=True)

    async def count_user_channels(self, user_id: int, premium: bool = False) -> int:
        table = self._get_table_name(premium)
        result = await self.execute_query(f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (user_id,), fetch_one=True)
        return result[0] if result else 0

    async def count_channel_posts(self, channel_id: int, premium: bool = False) -> int:
        channel_data = await self.get_channel_by_id(channel_id, premium)
        if not channel_data:
            return 0
        max_posts = 15 if premium else 3
        count = 0
        for i in range(1, max_posts + 1):
            post_idx = 2 + (i - 1) * 2
            if post_idx < len(channel_data) and channel_data[post_idx] is not None:
                count += 1
        return count

    async def is_premium(self, user_id: int) -> bool:
        return await self.is_premium_user(user_id)

    async def get_total_users(self) -> int:
        result = await self.execute_query("SELECT COUNT(*) FROM users", fetch_one=True)
        return result[0] if result else 0

    async def get_premium_users_count(self) -> int:
        result = await self.execute_query("SELECT COUNT(*) FROM users WHERE subscription = TRUE", fetch_one=True)
        return result[0] if result else 0

    async def get_total_channels(self) -> int:
        free = await self.execute_query("SELECT COUNT(*) FROM channel", fetch_one=True)
        premium = await self.execute_query("SELECT COUNT(*) FROM premium_channel", fetch_one=True)
        return (free[0] if free else 0) + (premium[0] if premium else 0)

    async def get_all_user_ids(self):
        return await self.execute_query("SELECT id FROM users", fetch_all=True)

    async def delete_channel(self, channel_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        await self.execute_query(f"DELETE FROM {table} WHERE id = ?", (channel_id,))

    async def get_channel_posts(self, channel_id: int, premium: bool = False):
        channel_data = await self.get_channel_by_id(channel_id, premium)
        if not channel_data:
            return []
        posts = []
        max_posts = 15 if premium else 3
        for i in range(1, max_posts + 1):
            post_idx = 2 + (i - 1) * 2
            theme_idx = post_idx + 1
            post_time = channel_data[post_idx] if len(channel_data) > post_idx else None
            post_theme = channel_data[theme_idx] if len(channel_data) > theme_idx else None
            if post_time and post_theme:
                posts.append({'post_num': i, 'time': post_time, 'theme': post_theme})
        return posts

    async def update_single_post(self, channel_id: int, post_num: int, time: str = None, theme: str = None, premium: bool = False):
        table = self._get_table_name(premium)
        try:
            if time:
                await self._check_24h_restriction(channel_id, premium)
            if time and theme:
                await self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ? WHERE id = ?", (time, theme, channel_id))
            elif time:
                await self.execute_query(f"UPDATE {table} SET post{post_num} = ? WHERE id = ?", (time, channel_id))
            elif theme:
                await self.execute_query(f"UPDATE {table} SET theme{post_num} = ? WHERE id = ?", (theme, channel_id))
            if time:
                await self.update_last_edit_time(channel_id, datetime.now(TZ).isoformat(), premium=premium)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update single post {post_num} for {channel_id}: {e}")
            raise

    async def delete_single_post(self, channel_id: int, post_num: int, premium: bool = False):
        table = self._get_table_name(premium)
        if premium:
            await self.execute_query(f"UPDATE {table} SET post{post_num} = NULL, theme{post_num} = NULL, image{post_num} = NULL WHERE id = ?", (channel_id,))
        else:
            await self.execute_query(f"UPDATE {table} SET post{post_num} = NULL, theme{post_num} = NULL WHERE id = ?", (channel_id,))

    async def get_next_available_post_num(self, channel_id: int, premium: bool = False) -> int:
        max_posts = 15 if premium else 3
        channel_data = await self.get_channel_by_id(channel_id, premium)
        if not channel_data:
            return 1
        for i in range(1, max_posts + 1):
            post_idx = 2 + (i - 1) * 2
            if post_idx >= len(channel_data) or channel_data[post_idx] is None:
                return i
        return None

    async def add_new_post(self, channel_id: int, post_num: int, time: str, theme: str, premium: bool = False, with_image: str = 'no'):
        table = self._get_table_name(premium)
        if premium:
            await self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ?, image{post_num} = ? WHERE id = ?", (time, theme, with_image, channel_id))
        else:
            await self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ? WHERE id = ?", (time, theme, channel_id))

    async def get_last_edit_time(self, channel_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        result = await self.execute_query(f"SELECT last_edit_time FROM {table} WHERE id = ?", (channel_id,), fetch_one=True)
        return result[0] if result and result[0] else None

    async def update_last_edit_time(self, channel_id: int, edit_time: str, premium: bool = False):
        table = self._get_table_name(premium)
        await self.execute_query(f"UPDATE {table} SET last_edit_time = ? WHERE id = ?", (edit_time, channel_id))

    # ============== Daily Stats Methods ==============

    async def count_total_active_posts(self) -> tuple:
        total = 0
        with_image = 0

        free_channels = await self.execute_query("SELECT * FROM channel", fetch_all=True)
        for ch in free_channels:
            for i in range(1, 4):
                post_idx = 2 + (i - 1) * 2
                if post_idx < len(ch) and ch[post_idx]:
                    total += 1

        premium_channels = await self.execute_query("SELECT * FROM premium_channel", fetch_all=True)
        for ch in premium_channels:
            for i in range(1, 16):
                post_idx = 2 + (i - 1) * 2
                image_idx = 32 + (i - 1)
                if post_idx < len(ch) and ch[post_idx]:
                    total += 1
                    if image_idx < len(ch) and ch[image_idx] == 'yes':
                        with_image += 1

        return total, with_image

    async def record_daily_stats(self):
        today = datetime.now(TZ).strftime("%Y-%m-%d")
        total_users = await self.get_total_users()
        premium_users = await self.get_premium_users_count()
        total_channels = await self.get_total_channels()
        total_posts, posts_with_image = await self.count_total_active_posts()

        await self.execute_query(
            """INSERT INTO daily_stats (date, total_users, premium_users, total_channels, total_posts, posts_with_image)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (date) DO UPDATE SET
               total_users = excluded.total_users,
               premium_users = excluded.premium_users,
               total_channels = excluded.total_channels,
               total_posts = excluded.total_posts,
               posts_with_image = excluded.posts_with_image""",
            (today, total_users, premium_users, total_channels, total_posts, posts_with_image)
        )
        logger.info(f"Daily stats recorded: {today} | users={total_users} premium={premium_users} "
                     f"channels={total_channels} posts={total_posts} img={posts_with_image}")

    async def get_stats_history(self, days: int = 30):
        return await self.execute_query(
            "SELECT date, total_users, premium_users, total_channels, total_posts, posts_with_image "
            "FROM daily_stats ORDER BY date DESC LIMIT ?",
            (days,), fetch_all=True
        )

    # ============== Referral Methods ==============

    async def add_referral(self, referrer_id: int, referred_id: int):
        await self.execute_query(
            "INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?) ON CONFLICT (referred_id) DO NOTHING",
            (referrer_id, referred_id)
        )
        await self.execute_query(
            "UPDATE users SET referred_by = ? WHERE id = ?",
            (referrer_id, referred_id)
        )

    async def activate_referral(self, referred_id: int):
        await self.execute_query(
            "UPDATE referrals SET activated = TRUE, activated_at = CURRENT_TIMESTAMP WHERE referred_id = ? AND activated = FALSE",
            (referred_id,)
        )

    async def get_referral_count(self, referrer_id: int, activated_only: bool = True) -> int:
        if activated_only:
            result = await self.execute_query(
                "SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND activated = TRUE",
                (referrer_id,), fetch_one=True
            )
        else:
            result = await self.execute_query(
                "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?",
                (referrer_id,), fetch_one=True
            )
        return result[0] if result else 0

    async def get_referrer_of(self, referred_id: int) -> int | None:
        result = await self.execute_query(
            "SELECT referrer_id FROM referrals WHERE referred_id = ?",
            (referred_id,), fetch_one=True
        )
        return result[0] if result else None

    async def has_activated_referral(self, referred_id: int) -> bool:
        result = await self.execute_query(
            "SELECT 1 FROM referrals WHERE referred_id = ? AND activated = TRUE",
            (referred_id,), fetch_one=True
        )
        return result is not None

    async def get_top_referrers(self, limit: int = 25):
        return await self.execute_query(
            "SELECT referrer_id, COUNT(*) as cnt FROM referrals WHERE activated = TRUE "
            "GROUP BY referrer_id ORDER BY cnt DESC LIMIT ?",
            (limit,), fetch_all=True
        )

    async def get_referral_stats(self) -> dict:
        total = await self.execute_query(
            "SELECT COUNT(*) FROM referrals", fetch_one=True
        )
        activated = await self.execute_query(
            "SELECT COUNT(*) FROM referrals WHERE activated = TRUE", fetch_one=True
        )
        participants = await self.execute_query(
            "SELECT COUNT(DISTINCT referrer_id) FROM referrals", fetch_one=True
        )
        return {
            'total_referrals': total[0] if total else 0,
            'activated_referrals': activated[0] if activated else 0,
            'total_participants': participants[0] if participants else 0,
        }

    async def get_user_premium_info(self, user_id: int) -> tuple | None:
        return await self.execute_query(
            "SELECT subscription, premium_type, start_date, end_date, referral_base_date FROM users WHERE id = ?",
            (user_id,), fetch_one=True
        )

    async def set_referral_base_date(self, user_id: int, base_date: str):
        await self.execute_query(
            "UPDATE users SET referral_base_date = ? WHERE id = ?",
            (base_date, user_id)
        )

    async def get_referral_base_date(self, user_id: int) -> str | None:
        result = await self.execute_query(
            "SELECT referral_base_date FROM users WHERE id = ?",
            (user_id,), fetch_one=True
        )
        return result[0] if result and result[0] else None


db = DatabaseManager()
