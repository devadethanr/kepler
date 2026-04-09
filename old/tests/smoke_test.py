from __future__ import annotations

import argparse
import asyncio

from swingtradev3.logging_config import setup_logging
from swingtradev3.models import AlertLevel
from swingtradev3.notifications.telegram_client import TelegramClient
from swingtradev3.paths import ensure_runtime_dirs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a Telegram smoke-test message")
    parser.add_argument(
        "--message",
        default="swingtradev3 Telegram smoke test",
        help="Message body to send",
    )
    parser.add_argument(
        "--level",
        choices=[level.value for level in AlertLevel],
        default=AlertLevel.INFO.value,
        help="Alert level prefix",
    )
    return parser


async def _run(message: str, level: str) -> int:
    client = TelegramClient()
    await client.send_text(message, level=AlertLevel(level))
    return 0


def main() -> None:
    ensure_runtime_dirs()
    setup_logging()
    args = _build_parser().parse_args()
    raise SystemExit(asyncio.run(_run(args.message, args.level)))


if __name__ == "__main__":
    main()
