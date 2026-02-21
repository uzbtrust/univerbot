import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Tuple
from contextlib import contextmanager

from sqlalchemy import create_engine, text, event
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Asia/Tashkent")
ALLOWED_TABLES = {"channel", "premium_channel"}

DB_URL = "sqlite:///database.db"


class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
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
            return
        self._initialized = True
        self._engine = create_engine(
            DB_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        @event.listens_for(self._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")
            cursor.close()

        self._init_database()

    def _init_database(self):
        with self._engine.begin() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS superadmins (
                    id INTEGER PRIMARY KEY
                )
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    subscription BOOLEAN DEFAULT 0,
                    premium_type TEXT,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP
                )
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS channel (
                    user_id INTEGER,
                    id INTEGER PRIMARY KEY,
                    post1 TEXT, theme1 TEXT,
                    post2 TEXT, theme2 TEXT,
                    post3 TEXT, theme3 TEXT
                )
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS premium_channel (
                    user_id INTEGER,
                    id INTEGER PRIMARY KEY,
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
                    post15 TEXT, theme15 TEXT
                )
            '''))

            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_subscription ON users(subscription);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_channel_user_id ON channel(user_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_premium_channel_user_id ON premium_channel(user_id);"))

            for i in range(1, 4):
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_channel_post{i} ON channel(post{i});"))
            for i in range(1, 16):
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_premium_post{i} ON premium_channel(post{i});"))

            self._add_column_if_not_exists(conn, "channel", "with_image", "BOOLEAN DEFAULT 0")
            self._add_column_if_not_exists(conn, "premium_channel", "with_image", "BOOLEAN DEFAULT 0")
            for i in range(1, 16):
                self._add_column_if_not_exists(conn, "premium_channel", f"image{i}", "TEXT DEFAULT 'no'")
            self._add_column_if_not_exists(conn, "channel", "last_edit_time", "TIMESTAMP")
            self._add_column_if_not_exists(conn, "premium_channel", "last_edit_time", "TIMESTAMP")

        logger.info("Database tables initialized (SQLAlchemy)")

    def _add_column_if_not_exists(self, conn, table_name: str, column_name: str, column_def: str):
        if table_name not in ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
        try:
            result = conn.execute(text(f"PRAGMA table_info({table_name})"))
            columns = [row[1] for row in result.fetchall()]
            if column_name not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"))
                logger.info(f"Added column {column_name} to {table_name}")
        except Exception as e:
            logger.warning(f"Could not add column {column_name} to {table_name}: {e}")

    @contextmanager
    def get_connection(self):
        conn = self._engine.connect()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
        with self._engine.connect() as conn:
            # SQLAlchemy text() bilan ? ni :p0, :p1 ga o'girish
            sa_query = query
            sa_params = {}
            for i, val in enumerate(params):
                sa_query = sa_query.replace("?", f":p{i}", 1)
                sa_params[f"p{i}"] = val

            result = conn.execute(text(sa_query), sa_params)

            if fetch_one:
                row = result.fetchone()
                return tuple(row) if row else None
            elif fetch_all:
                rows = result.fetchall()
                return [tuple(r) for r in rows]

            conn.commit()
            return result.lastrowid

    def close_all(self):
        self._engine.dispose()
        logger.info("Database engine disposed")

    # ============== User Methods ==============

    def user_exists(self, user_id: int) -> bool:
        result = self.execute_query("SELECT 1 FROM users WHERE id = ?", (user_id,), fetch_one=True)
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
        result = self.execute_query("SELECT subscription FROM users WHERE id = ?", (user_id,), fetch_one=True)
        is_premium = bool(result and result[0] == 1)
        self._premium_cache[user_id] = (is_premium, now)
        self._cleanup_cache_if_needed()
        return is_premium

    def is_superadmin(self, user_id: int) -> bool:
        result = self.execute_query("SELECT 1 FROM superadmins WHERE id = ?", (user_id,), fetch_one=True)
        return result is not None

    def add_user(self, user_id: int, subscription: bool = False):
        self.execute_query("INSERT OR IGNORE INTO users (id, subscription) VALUES (?, ?)", (user_id, subscription))

    def add_superadmin(self, user_id: int):
        self.execute_query("INSERT OR IGNORE INTO superadmins (id) VALUES (?)", (user_id,))

    def update_user_subscription(self, user_id: int, subscription: bool, premium_type: Optional[str] = None):
        if premium_type:
            self.execute_query("UPDATE users SET subscription = ?, premium_type = ? WHERE id = ?", (subscription, premium_type, user_id))
        else:
            self.execute_query("UPDATE users SET subscription = ? WHERE id = ?", (subscription, user_id))
        if user_id in self._premium_cache:
            del self._premium_cache[user_id]

    # ============== Channel Methods ==============

    def _get_table_name(self, premium: bool) -> str:
        return "premium_channel" if premium else "channel"

    def get_user_channels(self, user_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        return self.execute_query(f"SELECT * FROM {table} WHERE user_id = ?", (user_id,), fetch_all=True)

    def channel_exists(self, channel_id: int, premium: bool = False) -> bool:
        table = self._get_table_name(premium)
        result = self.execute_query(f"SELECT 1 FROM {table} WHERE id = ?", (channel_id,), fetch_one=True)
        return result is not None

    def add_channel(self, channel_id: int, user_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        self.execute_query(f"INSERT INTO {table} (id, user_id) VALUES (?, ?)", (channel_id, user_id))

    def _check_24h_restriction(self, channel_id: int, premium: bool):
        last_edit = self.get_last_edit_time(channel_id, premium=premium)
        if last_edit:
            try:
                last_dt = datetime.fromisoformat(last_edit)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=TZ)
            except ValueError:
                last_dt = None
            if last_dt and datetime.now(TZ) - last_dt < timedelta(hours=24):
                raise ValueError("Post vaqtini faqat 24 soatdan keyin o'zgartirish mumkin.")

    def update_channel_post(self, channel_id: int, post_num: int, time: str, theme: str, premium: bool = False, with_image: str = 'no', skip_24h_check: bool = False):
        table = self._get_table_name(premium)
        try:
            if not skip_24h_check:
                self._check_24h_restriction(channel_id, premium)
            if premium:
                self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ?, image{post_num} = ? WHERE id = ?", (time, theme, with_image, channel_id))
            else:
                self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ? WHERE id = ?", (time, theme, channel_id))
            if not skip_24h_check:
                self.update_last_edit_time(channel_id, datetime.now(TZ).isoformat(), premium=premium)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update channel post {post_num} for {channel_id}: {e}")
            raise

    def get_channel_by_id(self, channel_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        return self.execute_query(f"SELECT * FROM {table} WHERE id = ?", (channel_id,), fetch_one=True)

    def count_user_channels(self, user_id: int, premium: bool = False) -> int:
        table = self._get_table_name(premium)
        result = self.execute_query(f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (user_id,), fetch_one=True)
        return result[0] if result else 0

    def count_channel_posts(self, channel_id: int, premium: bool = False) -> int:
        channel_data = self.get_channel_by_id(channel_id, premium)
        if not channel_data:
            return 0
        max_posts = 15 if premium else 3
        count = 0
        for i in range(1, max_posts + 1):
            post_idx = 2 + (i - 1) * 2
            if post_idx < len(channel_data) and channel_data[post_idx] is not None:
                count += 1
        return count

    def is_premium(self, user_id: int) -> bool:
        return self.is_premium_user(user_id)

    def get_total_users(self) -> int:
        result = self.execute_query("SELECT COUNT(*) FROM users", fetch_one=True)
        return result[0] if result else 0

    def get_premium_users_count(self) -> int:
        result = self.execute_query("SELECT COUNT(*) FROM users WHERE subscription = 1", fetch_one=True)
        return result[0] if result else 0

    def get_total_channels(self) -> int:
        free = self.execute_query("SELECT COUNT(*) FROM channel", fetch_one=True)
        premium = self.execute_query("SELECT COUNT(*) FROM premium_channel", fetch_one=True)
        return (free[0] if free else 0) + (premium[0] if premium else 0)

    def get_all_user_ids(self):
        return self.execute_query("SELECT id FROM users", fetch_all=True)

    def delete_channel(self, channel_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        self.execute_query(f"DELETE FROM {table} WHERE id = ?", (channel_id,))

    def get_channel_posts(self, channel_id: int, premium: bool = False):
        channel_data = self.get_channel_by_id(channel_id, premium)
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

    def update_single_post(self, channel_id: int, post_num: int, time: str = None, theme: str = None, premium: bool = False):
        table = self._get_table_name(premium)
        try:
            if time:
                self._check_24h_restriction(channel_id, premium)
            if time and theme:
                self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ? WHERE id = ?", (time, theme, channel_id))
            elif time:
                self.execute_query(f"UPDATE {table} SET post{post_num} = ? WHERE id = ?", (time, channel_id))
            elif theme:
                self.execute_query(f"UPDATE {table} SET theme{post_num} = ? WHERE id = ?", (theme, channel_id))
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
            self.execute_query(f"UPDATE {table} SET post{post_num} = NULL, theme{post_num} = NULL, image{post_num} = NULL WHERE id = ?", (channel_id,))
        else:
            self.execute_query(f"UPDATE {table} SET post{post_num} = NULL, theme{post_num} = NULL WHERE id = ?", (channel_id,))

    def get_next_available_post_num(self, channel_id: int, premium: bool = False) -> int:
        max_posts = 15 if premium else 3
        channel_data = self.get_channel_by_id(channel_id, premium)
        if not channel_data:
            return 1
        for i in range(1, max_posts + 1):
            post_idx = 2 + (i - 1) * 2
            if post_idx >= len(channel_data) or channel_data[post_idx] is None:
                return i
        return None

    def add_new_post(self, channel_id: int, post_num: int, time: str, theme: str, premium: bool = False, with_image: str = 'no'):
        table = self._get_table_name(premium)
        if premium:
            self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ?, image{post_num} = ? WHERE id = ?", (time, theme, with_image, channel_id))
        else:
            self.execute_query(f"UPDATE {table} SET post{post_num} = ?, theme{post_num} = ? WHERE id = ?", (time, theme, channel_id))

    def get_last_edit_time(self, channel_id: int, premium: bool = False):
        table = self._get_table_name(premium)
        result = self.execute_query(f"SELECT last_edit_time FROM {table} WHERE id = ?", (channel_id,), fetch_one=True)
        return result[0] if result and result[0] else None

    def update_last_edit_time(self, channel_id: int, edit_time: str, premium: bool = False):
        table = self._get_table_name(premium)
        self.execute_query(f"UPDATE {table} SET last_edit_time = ? WHERE id = ?", (edit_time, channel_id))


db = DatabaseManager()
