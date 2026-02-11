import sqlite3
import time
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Tuple, List
import os

logger = logging.getLogger(__name__)

# Toshkent vaqt zonasi
TZ = ZoneInfo("Asia/Tashkent")

ALLOWED_TABLES = {"channel", "premium_channel"}


class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _db_path: str = "database.db"
    _premium_cache: Dict[int, Tuple[bool, float]] = {}
    _cache_ttl_seconds: int = 300
    _cache_max_size: int = 10000

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            # Har safar database mavjudligini tekshirish
            self._ensure_database_exists()
            return
        self._initialized = True
        self._init_database()

    def _ensure_database_exists(self):
        """Database fayli va jadvallar mavjudligini tekshirish"""
        try:
            # Fayl mavjud va hajmi 0 dan katta ekanligini tekshirish
            if not os.path.exists(self._db_path) or os.path.getsize(self._db_path) == 0:
                logger.warning("Database file is missing or empty, reinitializing...")
                self._init_database()
                return

            # Jadvallar mavjudligini tekshirish
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if cursor.fetchone() is None:
                    logger.warning("Database tables missing, reinitializing...")
                    self._init_database()
        except Exception as e:
            logger.error(f"Error checking database: {e}")
            self._init_database()

    def _init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS superadmins (
                    id INTEGER PRIMARY KEY
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    subscription BOOLEAN DEFAULT 0,
                    premium_type TEXT,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS channel (
                    user_id INTEGER,
                    id INTEGER PRIMARY KEY,
                    post1 TEXT,
                    theme1 TEXT,
                    post2 TEXT,
                    theme2 TEXT,
                    post3 TEXT,
                    theme3 TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS premium_channel (
                    user_id INTEGER,
                    id INTEGER PRIMARY KEY,
                    post1 TEXT,
                    theme1 TEXT,
                    post2 TEXT,
                    theme2 TEXT,
                    post3 TEXT,
                    theme3 TEXT,
                    post4 TEXT,
                    theme4 TEXT,
                    post5 TEXT,
                    theme5 TEXT,
                    post6 TEXT,
                    theme6 TEXT,
                    post7 TEXT,
                    theme7 TEXT,
                    post8 TEXT,
                    theme8 TEXT,
                    post9 TEXT,
                    theme9 TEXT,
                    post10 TEXT,
                    theme10 TEXT,
                    post11 TEXT,
                    theme11 TEXT,
                    post12 TEXT,
                    theme12 TEXT,
                    post13 TEXT,
                    theme13 TEXT,
                    post14 TEXT,
                    theme14 TEXT,
                    post15 TEXT,
                    theme15 TEXT
                )
            ''')

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_channel_user_id ON channel(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_premium_channel_user_id ON premium_channel(user_id);")

            self._add_column_if_not_exists(cursor, "channel", "with_image", "BOOLEAN DEFAULT 0")
            self._add_column_if_not_exists(cursor, "premium_channel", "with_image", "BOOLEAN DEFAULT 0")

            for i in range(1, 16):
                self._add_column_if_not_exists(cursor, "premium_channel", f"image{i}", "TEXT DEFAULT 'no'")

            self._add_column_if_not_exists(cursor, "channel", "last_edit_time", "TIMESTAMP")
            self._add_column_if_not_exists(cursor, "premium_channel", "last_edit_time", "TIMESTAMP")

            conn.commit()
            logger.info("Database tables initialized successfully")

    def _add_column_if_not_exists(self, cursor, table_name: str, column_name: str, column_def: str):
        if table_name not in ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]

            if column_name not in columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
                logger.info(f"Added column {column_name} to {table_name} table")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not add column {column_name} to {table_name}: {e}")

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()

            conn.commit()
            return cursor.lastrowid

    def user_exists(self, user_id: int) -> bool:
        result = self.execute_query(
            "SELECT 1 FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
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

    def is_premium_user(self, user_id: int) -> bool:
        now = time.time()
        cached = self._premium_cache.get(user_id)
        if cached and now - cached[1] < self._cache_ttl_seconds:
            return cached[0]

        if self.is_superadmin(user_id):
            self._premium_cache[user_id] = (True, now)
            self._cleanup_cache_if_needed()
            return True

        result = self.execute_query(
            "SELECT subscription FROM users WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
        is_premium = bool(result and result[0] == 1)
        self._premium_cache[user_id] = (is_premium, now)
        self._cleanup_cache_if_needed()
        return is_premium

    def is_superadmin(self, user_id: int) -> bool:
        result = self.execute_query(
            "SELECT 1 FROM superadmins WHERE id = ?",
            (user_id,),
            fetch_one=True
        )
        return result is not None

    def add_user(self, user_id: int, subscription: bool = False):
        self.execute_query(
            "INSERT OR IGNORE INTO users (id, subscription) VALUES (?, ?)",
            (user_id, subscription)
        )

    def add_superadmin(self, user_id: int):
        self.execute_query(
            "INSERT OR IGNORE INTO superadmins (id) VALUES (?)",
            (user_id,)
        )

    def update_user_subscription(self, user_id: int, subscription: bool, premium_type: Optional[str] = None):
        if premium_type:
            self.execute_query(
                "UPDATE users SET subscription = ?, premium_type = ? WHERE id = ?",
                (subscription, premium_type, user_id)
            )
        else:
            self.execute_query(
                "UPDATE users SET subscription = ? WHERE id = ?",
                (subscription, user_id)
            )

        if user_id in self._premium_cache:
            del self._premium_cache[user_id]

    def _get_table_name(self, premium: bool) -> str:
        return "premium_channel" if premium else "channel"

    def get_user_channels(self, user_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        return self.execute_query(
            f"SELECT * FROM {table} WHERE user_id = ?",
            (user_id,),
            fetch_all=True
        )

    def channel_exists(self, channel_id: int, premium: bool = False) -> bool:
        table = self._get_table_name(premium)
        result = self.execute_query(
            f"SELECT 1 FROM {table} WHERE id = ?",
            (channel_id,),
            fetch_one=True
        )
        return result is not None

    def add_channel(self, channel_id: int, user_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        self.execute_query(
            f"INSERT INTO {table} (id, user_id) VALUES (?, ?)",
            (channel_id, user_id)
        )

    def _check_24h_restriction(self, channel_id: int, premium: bool):
        last_edit = self.get_last_edit_time(channel_id, premium=premium)
        if last_edit:
            try:
                last_dt = datetime.fromisoformat(last_edit)
                # Agar timezone yo'q bo'lsa, TZ qo'shamiz
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=TZ)
            except ValueError:
                last_dt = None
            if last_dt and datetime.now(TZ) - last_dt < timedelta(hours=24):
                raise ValueError("Post vaqtini faqat 24 soatdan keyin o'zgartirish mumkin.")

    def update_channel_post(self, channel_id: int, post_num: int, time: str, theme: str, premium: bool = False, with_image: str = 'no', skip_24h_check: bool = False):
        """
        Post qo'shish yoki yangilash.
        skip_24h_check=True bo'lsa 24 soatlik cheklov tekshirilmaydi (yangi post qo'shish uchun)
        """
        table = self._get_table_name(premium)
        try:
            # Faqat mavjud postni o'zgartirganda 24h tekshiruvi
            if not skip_24h_check:
                self._check_24h_restriction(channel_id, premium)

            if premium:
                self.execute_query(
                    f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ?, image{post_num} = ? WHERE id = ?",
                    (time, theme, with_image, channel_id)
                )
            else:
                self.execute_query(
                    f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ? WHERE id = ?",
                    (time, theme, channel_id)
                )

            # Faqat vaqt o'zgartirilganda last_edit_time yangilanadi
            if not skip_24h_check:
                self.update_last_edit_time(channel_id, datetime.now(TZ).isoformat(), premium=premium)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update channel post {post_num} for {channel_id}: {e}")
            raise

    def get_channel_by_id(self, channel_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        return self.execute_query(
            f"SELECT * FROM {table} WHERE id = ?",
            (channel_id,),
            fetch_one=True
        )

    def count_user_channels(self, user_id: int, premium: bool = False) -> int:
        table = self._get_table_name(premium)
        result = self.execute_query(
            f"SELECT COUNT(*) FROM {table} WHERE user_id = ?",
            (user_id,),
            fetch_one=True
        )
        return result[0] if result else 0

    def count_channel_posts(self, channel_id: int, premium: bool = False) -> int:
        """Kanalda mavjud postlar sonini hisoblash"""
        channel_data = self.get_channel_by_id(channel_id, premium)
        if not channel_data:
            return 0

        # sqlite3.Row ni tuple ga aylantirish
        channel_tuple = tuple(channel_data)
        max_posts = 15 if premium else 3
        count = 0

        for i in range(1, max_posts + 1):
            # channel jadvalida: user_id, id, post1, theme1, post2, theme2, ...
            # premium_channel jadvalida: user_id, id, post1, theme1, post2, theme2, ..., image1, image2, ...
            post_idx = 2 + (i - 1) * 2  # post1 = index 2, post2 = index 4, ...

            if post_idx < len(channel_tuple) and channel_tuple[post_idx] is not None:
                count += 1

        return count

    def is_premium(self, user_id: int) -> bool:
        """is_premium_user aliasi - qulaylik uchun"""
        return self.is_premium_user(user_id)

    def get_total_users(self) -> int:
        result = self.execute_query(
            "SELECT COUNT(*) FROM users",
            fetch_one=True
        )
        return result[0] if result else 0

    def get_premium_users_count(self) -> int:
        result = self.execute_query(
            "SELECT COUNT(*) FROM users WHERE subscription = 1",
            fetch_one=True
        )
        return result[0] if result else 0

    def get_total_channels(self) -> int:
        free_result = self.execute_query(
            "SELECT COUNT(*) FROM channel",
            fetch_one=True
        )
        premium_result = self.execute_query(
            "SELECT COUNT(*) FROM premium_channel",
            fetch_one=True
        )
        free_count = free_result[0] if free_result else 0
        premium_count = premium_result[0] if premium_result else 0
        return free_count + premium_count

    def get_all_user_ids(self):
        return self.execute_query(
            "SELECT id FROM users",
            fetch_all=True
        )

    def delete_channel(self, channel_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        self.execute_query(
            f"DELETE FROM {table} WHERE id = ?",
            (channel_id,)
        )

    def get_channel_posts(self, channel_id: int, premium: bool = False):
        channel_data = self.get_channel_by_id(channel_id, premium)
        if not channel_data:
            logger.debug(f"get_channel_posts: No channel found for id={channel_id}, premium={premium}")
            return []

        # sqlite3.Row ni tuple ga aylantirish (indeks bilan ishlash uchun)
        channel_tuple = tuple(channel_data)
        logger.debug(f"get_channel_posts: channel_id={channel_id}, premium={premium}, columns={len(channel_tuple)}")

        posts = []
        max_posts = 15 if premium else 3
        # Jadval strukturasi: user_id(0), id(1), post1(2), theme1(3), post2(4), theme2(5), ...
        for i in range(1, max_posts + 1):
            post_idx = 2 + (i - 1) * 2  # post1=2, post2=4, post3=6, ...
            theme_idx = post_idx + 1    # theme1=3, theme2=5, theme3=7, ...

            post_time = channel_tuple[post_idx] if len(channel_tuple) > post_idx else None
            post_theme = channel_tuple[theme_idx] if len(channel_tuple) > theme_idx else None

            if post_time and post_theme:
                posts.append({
                    'post_num': i,
                    'time': post_time,
                    'theme': post_theme
                })
                logger.debug(f"  Found post {i}: time={post_time}, theme={post_theme}")

        logger.debug(f"get_channel_posts: Total {len(posts)} posts found")
        return posts

    def update_single_post(self, channel_id: int, post_num: int, time: str = None, theme: str = None, premium: bool = False):
        table = self._get_table_name(premium)
        try:
            if time:
                self._check_24h_restriction(channel_id, premium)

            if time and theme:
                self.execute_query(
                    f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ? WHERE id = ?",
                    (time, theme, channel_id)
                )
            elif time:
                self.execute_query(
                    f"UPDATE {table} SET post{post_num} = ? WHERE id = ?",
                    (time, channel_id)
                )
            elif theme:
                self.execute_query(
                    f"UPDATE {table} SET theme{post_num} = ? WHERE id = ?",
                    (theme, channel_id)
                )

            if time:
                self.update_last_edit_time(channel_id, datetime.now(TZ).isoformat(), premium=premium)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update single post {post_num} for {channel_id}: {e}")
            raise

    def delete_single_post(self, channel_id: int, post_num: int, premium: bool = False):
        table = self._get_table_name(premium)
        if premium:
            self.execute_query(
                f"UPDATE {table} SET post{post_num} = NULL, theme{post_num} = NULL, image{post_num} = NULL WHERE id = ?",
                (channel_id,)
            )
        else:
            self.execute_query(
                f"UPDATE {table} SET post{post_num} = NULL, theme{post_num} = NULL WHERE id = ?",
                (channel_id,)
            )

    def get_next_available_post_num(self, channel_id: int, premium: bool = False) -> int:
        """Bo'sh post raqamini topish"""
        max_posts = 15 if premium else 3
        channel_data = self.get_channel_by_id(channel_id, premium)

        if not channel_data:
            return 1

        # sqlite3.Row ni tuple ga aylantirish
        channel_tuple = tuple(channel_data)

        # Jadval strukturasi: user_id(0), id(1), post1(2), theme1(3), post2(4), theme2(5), ...
        # post_idx = 2 + (i - 1) * 2
        for i in range(1, max_posts + 1):
            post_idx = 2 + (i - 1) * 2  # post1=2, post2=4, post3=6, ...

            if post_idx >= len(channel_tuple) or channel_tuple[post_idx] is None:
                return i

        return None

    def add_new_post(self, channel_id: int, post_num: int, time: str, theme: str, premium: bool = False, with_image: str = 'no'):
        table = self._get_table_name(premium)
        if premium:
            self.execute_query(
                f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ?, image{post_num} = ? WHERE id = ?",
                (time, theme, with_image, channel_id)
            )
        else:
            self.execute_query(
                f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ? WHERE id = ?",
                (time, theme, channel_id)
            )

    def get_last_edit_time(self, channel_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        result = self.execute_query(
            f"SELECT last_edit_time FROM {table} WHERE id = ?",
            (channel_id,),
            fetch_one=True
        )
        return result[0] if result and result[0] else None

    def update_last_edit_time(self, channel_id: int, edit_time: str, premium: bool = False):
        table = self._get_table_name(premium)
        self.execute_query(
            f"UPDATE {table} SET last_edit_time = ? WHERE id = ?",
            (edit_time, channel_id)
        )


db = DatabaseManager()
