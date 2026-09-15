"""Structured, PII-safe logging setup with RotatingFileHandler.

CRITICAL PRIVACY RULE:
Never log raw transcribed audio text, LLM responses, prompt contents, or
custom vocabulary terms. Only log performance metadata (durations in ms,
character counts, active application names, and error codes).
"""

from __future__ import annotations

import logging
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE_NAME = "morocovoice.log"
MAX_LOG_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3

_root_logger_initialized = False


class PIISafeFilter(logging.Filter):
    """Safety filter ensuring sensitive keywords or raw payload variables do not leak."""

    FORBIDDEN_KEYS = ("text", "prompt", "transcription", "llm_response", "vocabulary", "token")

    def filter(self, record: logging.LogRecord) -> bool:
        # Sanitize full formatted message to prevent leaks slipping through record.args
        try:
            full_msg = record.getMessage().lower()
        except Exception:
            full_msg = str(record.msg).lower()

        for key in self.FORBIDDEN_KEYS:
            if f'"{key}":' in full_msg or f"'{key}':" in full_msg or f"'{key}' ->" in full_msg:
                record.msg = "[REDACTED_PII_PAYLOAD]"
                record.args = ()
                break
        return True


def setup_logging(log_dir: str | Path | None = None) -> logging.Logger:
    """Initialize structured rotating file logging."""
    global _root_logger_initialized
    if _root_logger_initialized:
        return logging.getLogger("morocovoice")

    if log_dir is None:
        log_path = Path(LOG_FILE_NAME).resolve()
    else:
        log_path = (Path(log_dir) / LOG_FILE_NAME).resolve()

    logger = logging.getLogger("morocovoice")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Rotating file handler (5 MB x 3 backups)
    file_handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=MAX_LOG_SIZE_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(PIISafeFilter())
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(PIISafeFilter())
    logger.addHandler(console_handler)

    _root_logger_initialized = True
    logger.info("MorocoVoice logging subsystem initialized (PII-Safe RotatingFileHandler).")
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the morocovoice namespace."""
    if not _root_logger_initialized:
        setup_logging()
    return logging.getLogger(f"morocovoice.{name}")


def get_log_file_path() -> Path:
    """Return the absolute path to the active log file."""
    return Path(LOG_FILE_NAME).resolve()


def open_log_in_notepad() -> None:
    """Open voiceflow.log in Notepad for live diagnostics (Ctrl+Shift+D)."""
    log_path = get_log_file_path()
    if not log_path.exists():
        log_path.touch()
    try:
        subprocess.Popen(["notepad.exe", str(log_path)], close_fds=True)
    except Exception as e:
        get_logger("logging").error("Failed to open log in notepad: %s", type(e).__name__)
