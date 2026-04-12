from __future__ import annotations

import sys

from loguru import logger

from paths import LOGS_DIR, ensure_runtime_dirs


def setup_logging() -> None:
    ensure_runtime_dirs()
    
    # Custom format to include correlation_id if present
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[channel]}</cyan> | "
        "<magenta>{extra[correlation_id]}</magenta> - "
        "<level>{message}</level>"
    )

    logger.remove()
    logger.add(sys.stdout, format=log_format, level="INFO")
    logger.add(LOGS_DIR / "errors.log", level="ERROR", rotation="5 MB")
    logger.add(LOGS_DIR / "research.log", format=log_format, filter=lambda r: r["extra"].get("channel") == "research")
    logger.add(LOGS_DIR / "trades.log", format=log_format, filter=lambda r: r["extra"].get("channel") == "trades")
    logger.add(LOGS_DIR / "decisions.log", format=log_format, filter=lambda r: r["extra"].get("channel") == "decisions")


def get_logger(channel: str, correlation_id: str = "SYSTEM"):
    return logger.bind(channel=channel, correlation_id=correlation_id)
