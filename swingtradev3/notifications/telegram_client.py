from __future__ import annotations

import os

from swingtradev3.logging_config import get_logger
from swingtradev3.models import AlertLevel
from swingtradev3.notifications.formatter import NotificationFormatter


class TelegramClient:
    def __init__(self) -> None:
        self.log = get_logger("decisions")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self.formatter = NotificationFormatter()

    def _is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send_text(self, text: str, level: AlertLevel = AlertLevel.INFO) -> None:
        self.log.info("Telegram outbound: {}", text)
        if not self._is_configured():
            self.log.warning("Telegram is not configured; skipping outbound message")
            return
        try:
            from telegram import Bot
        except ImportError as exc:
            raise RuntimeError(
                "python-telegram-bot is required for Telegram notifications"
            ) from exc

        bot = Bot(token=self.bot_token)
        await bot.send_message(chat_id=self.chat_id, text=text, parse_mode="HTML")

    async def send_entry_alert(
        self,
        ticker: str,
        company_name: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
    ) -> None:
        message = self.formatter.entry_alert(
            ticker, company_name, quantity, entry_price, stop_loss, target
        )
        await self.send_text(message)

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
        message = self.formatter.profit_alert(
            ticker,
            company_name,
            quantity,
            entry_price,
            exit_price,
            pnl_amount,
            pnl_percent,
            exit_reason,
        )
        await self.send_text(message)

    async def send_approval_request(self, lines: list[str]) -> None:
        message = "📋 <b>MORNING BRIEFING</b>\n" + "━" * 20 + "\n"
        message += "\n".join(lines)
        await self.send_text(message)

    async def send_daily_summary(
        self,
        positions_count: int,
        pending_count: int,
        cash: float,
        unrealized_pnl: float,
        realized_pnl: float,
    ) -> None:
        message = self.formatter.daily_summary(
            positions_count, pending_count, cash, unrealized_pnl, realized_pnl
        )
        await self.send_text(message)

    async def send_no_setup(self) -> None:
        message = self.formatter.no_setup_alert()
        await self.send_text(message)

    async def send_system_status(self, message: str, is_warning: bool = False) -> None:
        message = self.formatter.system_status(message, is_warning)
        await self.send_text(message)
