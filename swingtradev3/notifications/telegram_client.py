from __future__ import annotations

import os

from swingtradev3.logging_config import get_logger
from swingtradev3.models import AlertLevel


class TelegramClient:
    def __init__(self) -> None:
        self.log = get_logger("decisions")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    def _is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send_text(self, text: str, level: AlertLevel = AlertLevel.INFO) -> None:
        prefix = f"[{level.value.upper()}] "
        message = prefix + text
        self.log.info("Telegram outbound: {}", message)
        if not self._is_configured():
            self.log.warning("Telegram is not configured; skipping outbound message")
            return
        try:
            from telegram import Bot
        except ImportError as exc:
            raise RuntimeError("python-telegram-bot is required for Telegram notifications") from exc

        bot = Bot(token=self.bot_token)
        await bot.send_message(chat_id=self.chat_id, text=message)

    async def send_approval_request(self, lines: list[str]) -> None:
        message = "Morning briefing\n" + "\n".join(lines)
        await self.send_text(message, level=AlertLevel.INFO)
