from __future__ import annotations

from swingtradev3.models import AlertLevel
from swingtradev3.notifications.telegram_client import TelegramClient


class AlertsTool:
    def __init__(self, client: TelegramClient | None = None) -> None:
        self.client = client or TelegramClient()

    async def send_alert(self, message: str, level: str = "info") -> None:
        await self.client.send_text(message, level=AlertLevel(level))

    async def send_approval_request(self, lines: list[str]) -> None:
        await self.client.send_approval_request(lines)
