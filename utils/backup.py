"""Kunlik PostgreSQL backup — SQL dump fayl yaratish."""

import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import text

from utils.database import db

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Asia/Tashkent")

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")
TABLES = ["superadmins", "users", "channel", "premium_channel", "daily_stats"]


def create_backup(backup_name: str = "backup.sql") -> str | None:
    """Barcha jadvallarni SQL dump qilib faylga yozish.

    Args:
        backup_name: Fayl nomi (default: backup.sql)

    Returns:
        Yaratilgan fayl yo'li yoki None
    """
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        timestamp = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(f"-- UniverBot Database Backup\n")
            f.write(f"-- Created: {timestamp}\n")
            f.write(f"-- Tables: {', '.join(TABLES)}\n\n")

            with db._engine.connect() as conn:
                for table_name in TABLES:
                    try:
                        # Jadval strukturasini olish
                        rows = conn.execute(text(f"SELECT * FROM {table_name}")).fetchall()
                        if not rows:
                            f.write(f"-- Table '{table_name}': empty\n\n")
                            continue

                        # Ustun nomlarini olish
                        columns = list(rows[0]._mapping.keys())
                        col_names = ", ".join(columns)

                        f.write(f"-- Table: {table_name} ({len(rows)} rows)\n")

                        for row in rows:
                            values = []
                            for val in row:
                                if val is None:
                                    values.append("NULL")
                                elif isinstance(val, bool):
                                    values.append("TRUE" if val else "FALSE")
                                elif isinstance(val, (int, float)):
                                    values.append(str(val))
                                else:
                                    escaped = str(val).replace("'", "''")
                                    values.append(f"'{escaped}'")

                            vals_str = ", ".join(values)
                            f.write(f"INSERT INTO {table_name} ({col_names}) VALUES ({vals_str}) ON CONFLICT DO NOTHING;\n")

                        f.write("\n")

                    except Exception as e:
                        logger.warning(f"Backup: '{table_name}' jadvalini eksport qilib bo'lmadi: {e}")
                        f.write(f"-- ERROR exporting table '{table_name}': {e}\n\n")

        file_size = os.path.getsize(backup_path)
        logger.info(f"Backup yaratildi: {backup_path} ({file_size} bytes)")
        return backup_path

    except Exception as e:
        logger.error(f"Backup yaratishda xatolik: {e}", exc_info=True)
        return None


def cleanup_old_backups(keep_last: int = 7):
    """Eski backuplarni tozalash, oxirgi N tasini qoldirish."""
    try:
        if not os.path.exists(BACKUP_DIR):
            return

        files = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")],
            key=lambda f: os.path.getmtime(os.path.join(BACKUP_DIR, f)),
            reverse=True
        )

        for old_file in files[keep_last:]:
            os.remove(os.path.join(BACKUP_DIR, old_file))
            logger.info(f"Eski backup o'chirildi: {old_file}")

    except Exception as e:
        logger.warning(f"Backup tozalashda xatolik: {e}")
