import sqlite3
import time
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List

logger = logging.getLogger(__name__)

ALLOWED_TABLES = {"channel", "premium_channel", "settings"}

DEFAULT_SETTINGS = {
    'SUPER_ADMIN1': os.getenv('SUPER_ADMIN1', '0'),
    'SUPER_ADMIN2': os.getenv('SUPER_ADMIN2', '0'),
    'ADMIN1_ACTIVE': '1',
    'ADMIN2_ACTIVE': '0',
    'CARD_NUMBER': os.getenv('CARD_NUMBER', ''),
    'CARD_NAME': os.getenv('CARD_NAME', ''),
    'CARD_SURNAME': os.getenv('CARD_SURNAME', ''),
    'WEEKLY_PRICE': os.getenv('WEEKLY_PRICE', '5000'),
    'DAY15_PRICE': os.getenv('DAY15_PRICE', '10000'),
    'MONTHLY_PRICE': os.getenv('MONTHLY_PRICE', '20000'),
    'MAX_CHANNELS_FREE': os.getenv('MAX_CHANNELS_FREE', '1'),
    'MAX_CHANNELS_PREMIUM': os.getenv('MAX_CHANNELS_PREMIUM', '3'),
    'MAX_POSTS_FREE': os.getenv('MAX_POSTS_FREE', '3'),
    'MAX_POSTS_PREMIUM': os.getenv('MAX_POSTS_PREMIUM', '15'),
    'MAX_THEME_WORDS_FREE': os.getenv('MAX_THEME_WORDS_FREE', '10'),
    'MAX_THEME_WORDS_PREMIUM': os.getenv('MAX_THEME_WORDS_PREMIUM', '15'),
    'IMAGE_MODE': os.getenv('IMAGE_MODE', 'OFF'),
}


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
            return
        self._initialized = True
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
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_cheques (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    subscription_type TEXT NOT NULL,
                    message_id_admin1 INTEGER,
                    message_id_admin2 INTEGER,
                    chat_id_admin1 INTEGER,
                    chat_id_admin2 INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

            self._init_default_settings(cursor)

            conn.commit()
            logger.info("Database tables initialized successfully")

    def _init_default_settings(self, cursor):
        for key, value in DEFAULT_SETTINGS.items():
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )

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
            except ValueError:
                last_dt = None
            if last_dt and datetime.utcnow() - last_dt < timedelta(hours=24):
                raise ValueError("Post vaqtini faqat 24 soatdan keyin o'zgartirish mumkin.")

    def update_channel_post(self, channel_id: int, post_num: int, time: str, theme: str, premium: bool = False, with_image: str = 'no'):
        table = self._get_table_name(premium)
        try:
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

            self.update_last_edit_time(channel_id, datetime.utcnow().isoformat(), premium=premium)
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
            return []

        posts = []
        for i in range(1, 16 if premium else 4):
            post_time = channel_data[i * 2] if len(channel_data) > i * 2 else None
            post_theme = channel_data[i * 2 + 1] if len(channel_data) > i * 2 + 1 else None

            if post_time and post_theme:
                posts.append({
                    'post_num': i,
                    'time': post_time,
                    'theme': post_theme
                })

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
                self.update_last_edit_time(channel_id, datetime.utcnow().isoformat(), premium=premium)
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
        max_posts = 15 if premium else 3
        channel_data = self.get_channel_by_id(channel_id, premium)

        if not channel_data:
            return 1

        for i in range(1, max_posts + 1):
            if premium:
                post_idx = 2 + (i - 1) * 3
            else:
                post_idx = 2 + (i - 1) * 2

            if post_idx >= len(channel_data) or channel_data[post_idx] is None:
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

    def get_setting(self, key: str, default: str = None) -> str:
        result = self.execute_query(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
            fetch_one=True
        )
        if result:
            return result[0]
        return default

    def set_setting(self, key: str, value: str) -> bool:
        try:
            self.execute_query(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False

    def get_all_settings(self) -> Dict[str, str]:
        result = self.execute_query(
            "SELECT key, value FROM settings",
            fetch_all=True
        )
        return {row[0]: row[1] for row in result} if result else {}

    def get_setting_int(self, key: str, default: int = 0) -> int:
        value = self.get_setting(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def get_active_admins(self) -> List[int]:
        admins = []
        admin1 = self.get_setting_int('SUPER_ADMIN1')
        admin2 = self.get_setting_int('SUPER_ADMIN2')
        admin1_active = self.get_setting('ADMIN1_ACTIVE', '1') == '1'
        admin2_active = self.get_setting('ADMIN2_ACTIVE', '0') == '1'

        if admin1 and admin1_active:
            admins.append(admin1)
        if admin2 and admin2_active:
            admins.append(admin2)

        return admins

    def add_pending_cheque(self, user_id: int, subscription_type: str,
                           msg_id_admin1: int = None, msg_id_admin2: int = None,
                           chat_id_admin1: int = None, chat_id_admin2: int = None) -> int:
        return self.execute_query(
            """INSERT INTO pending_cheques
               (user_id, subscription_type, message_id_admin1, message_id_admin2,
                chat_id_admin1, chat_id_admin2)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, subscription_type, msg_id_admin1, msg_id_admin2,
             chat_id_admin1, chat_id_admin2)
        )

    def get_pending_cheque_by_message(self, message_id: int, chat_id: int):
        result = self.execute_query(
            """SELECT * FROM pending_cheques
               WHERE (message_id_admin1 = ? AND chat_id_admin1 = ?)
                  OR (message_id_admin2 = ? AND chat_id_admin2 = ?)
               AND status = 'pending'""",
            (message_id, chat_id, message_id, chat_id),
            fetch_one=True
        )
        return result

    def update_cheque_status(self, cheque_id: int, status: str):
        self.execute_query(
            "UPDATE pending_cheques SET status = ? WHERE id = ?",
            (status, cheque_id)
        )

    def get_cheque_by_id(self, cheque_id: int):
        return self.execute_query(
            "SELECT * FROM pending_cheques WHERE id = ?",
            (cheque_id,),
            fetch_one=True
        )


db = DatabaseManager()
