from __future__ import annotations
import logging
import logging.handlers
import os
from typing import Optional

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_JSON = os.getenv("LOG_JSON", "0") == "1"
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.getenv("LOG_FILE", "bot.log")
MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(2 * 1024 * 1024)))
BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))

try:
    os.makedirs(LOG_DIR, exist_ok=True)
except OSError:
    pass

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        import json
        base = {
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


def configure_logging(level: Optional[str] = None) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    lvl = getattr(logging, (level or LOG_LEVEL), logging.INFO)
    root.setLevel(lvl)

    formatter: logging.Formatter
    if LOG_JSON:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(lvl)

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, LOG_FILE), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(lvl)

    root.addHandler(stream_handler)
    root.addHandler(file_handler)

__all__ = ["configure_logging"]
