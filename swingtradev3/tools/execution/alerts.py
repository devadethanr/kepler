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

    async def send_entry_alert(
        self,
        ticker: str,
        company_name: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
    ) -> None:
        await self.client.send_entry_alert(
            ticker, company_name, quantity, entry_price, stop_loss, target
        )

    async def send_profit_alert(
        self,
        ticker: str,
        company_name: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        pnl_amount: float,
        pnl_percent: float,
        exit_reason: str,
    ) -> None:
        await self.client.send_profit_alert(
            ticker,
            company_name,
            quantity,
            entry_price,
            exit_price,
            pnl_amount,
            pnl_percent,
            exit_reason,
        )

    async def send_daily_summary(
        self,
        positions_count: int,
        pending_count: int,
        cash: float,
        unrealized_pnl: float,
        realized_pnl: float,
    ) -> None:
        await self.client.send_daily_summary(
            positions_count, pending_count, cash, unrealized_pnl, realized_pnl
        )

    async def send_no_setup(self) -> None:
        await self.client.send_no_setup()

    async def send_system_status(self, message: str, is_warning: bool = False) -> None:
        await self.client.send_system_status(message, is_warning)
