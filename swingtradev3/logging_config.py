from __future__ import annotations

import sys

from loguru import logger

from .paths import LOGS_DIR, ensure_runtime_dirs


def setup_logging() -> None:
    ensure_runtime_dirs()
    logger.remove()
    logger.add(sys.stdout, level="INFO")
    logger.add(LOGS_DIR / "errors.log", level="ERROR", rotation="5 MB")
    logger.add(LOGS_DIR / "research.log", filter=lambda r: r["extra"].get("channel") == "research")
    logger.add(LOGS_DIR / "trades.log", filter=lambda r: r["extra"].get("channel") == "trades")
    logger.add(LOGS_DIR / "decisions.log", filter=lambda r: r["extra"].get("channel") == "decisions")


def get_logger(channel: str):
    return logger.bind(channel=channel)
