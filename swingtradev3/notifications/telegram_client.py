from __future__ import annotations

import os

from swingtradev3.logging_config import get_logger
from swingtradev3.models import AlertLevel


class TelegramClient:
    def __init__(self) -> None:
        self.log = get_logger("decisions")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    async def send_text(self, text: str, level: AlertLevel = AlertLevel.INFO) -> None:
        self.log.info("[{}] {}", level.value.upper(), text)

    async def send_approval_request(self, lines: list[str]) -> None:
        message = "Morning briefing\n" + "\n".join(lines)
        await self.send_text(message, level=AlertLevel.INFO)
