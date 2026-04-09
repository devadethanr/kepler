from __future__ import annotations

import os
from typing import Any

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
        self.log.info("Telegram outbound: {} chars", len(text))
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
        # Try plain text first (no parse_mode) to avoid any HTML issues
        try:
            await bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            # If plain fails, try with HTML
            self.log.warning("Plain text failed, trying HTML: {}", e)
            await bot.send_message(chat_id=self.chat_id, text=text, parse_mode="HTML")

    async def send_text_with_keyboard(
        self,
        text: str,
        keyboard: list[list[dict[str, str]]],
        level: AlertLevel = AlertLevel.INFO,
    ) -> int | None:
        """Send message with inline keyboard. Returns message_id for tracking replies."""
        self.log.info("Telegram outbound with keyboard: {}", text)
        if not self._is_configured():
            self.log.warning("Telegram is not configured; skipping outbound message")
            return None
        try:
            from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
        except ImportError as exc:
            raise RuntimeError(
                "python-telegram-bot is required for Telegram notifications"
            ) from exc

        bot = Bot(token=self.bot_token)

        # Build keyboard markup
        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        btn["text"], callback_data=btn["callback_data"]
                    )
                    for btn in row
                ]
                for row in keyboard
            ]
        )

        message = await bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
        return message.message_id

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

    async def send_approval_request(
        self,
        ticker: str,
        company_name: str,
        score: float,
        setup_type: str,
        entry_low: float,
        entry_high: float,
        stop_price: float,
        target_price: float,
        holding_days: int,
        reasoning: str,
    ) -> int | None:
        """Send approval request with YES/NO inline buttons."""
        message = self.formatter.approval_request(
            ticker=ticker,
            company_name=company_name,
            score=score,
            setup_type=setup_type,
            entry_zone_low=entry_low,
            entry_zone_high=entry_high,
            stop_loss=stop_price,
            target=target_price,
            holding_days=holding_days,
            reasoning=reasoning,
        )

        # YES/NO inline keyboard
        keyboard = [
            [
                {"text": "✅ YES", "callback_data": f"APPROVE:{ticker}"},
                {"text": "❌ NO", "callback_data": f"REJECT:{ticker}"},
            ]
        ]

        message_id = await self.send_text_with_keyboard(message, keyboard)
        self.log.info(
            "Sent approval request for {} with message_id {}", ticker, message_id
        )
        return message_id

    async def send_briefing(self, lines: list[str]) -> None:
        """Send morning briefing without approval buttons."""
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

    async def get_updates(
        self, offset: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get incoming updates (for polling)."""
        if not self._is_configured():
            return []

        try:
            from telegram import Bot
        except ImportError:
            return []

        bot = Bot(token=self.bot_token)
        updates = await bot.get_updates(offset=offset, limit=limit, timeout=30)

        return [
            {
                "update_id": update.update_id,
                "callback_query": {
                    "id": update.callback_query.id,
                    "data": update.callback_query.data,
                    "message_id": update.callback_query.message.message_id
                    if update.callback_query.message
                    else None,
                }
                if update.callback_query
                else None,
                "message": {
                    "text": update.message.text,
                    "chat_id": update.message.chat_id,
                    "message_id": update.message.message_id,
                }
                if update.message
                else None,
            }
            for update in updates
        ]

    async def answer_callback_query(self, callback_query_id: str, text: str) -> bool:
        """Acknowledge callback query (shows popup to user)."""
        if not self._is_configured():
            return False

        try:
            from telegram import Bot
        except ImportError:
            return False

        try:
            bot = Bot(token=self.bot_token)
            await bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text,
                show_alert=True,  # Force as alert for better visibility
            )
            return True
        except Exception as e:
            self.log.error("Failed to answer callback query: {}", e)
            return False

    async def edit_message_text(
        self,
        message_id: int,
        text: str,
        keyboard: list[list[dict[str, str]]] | None = None,
    ) -> None:
        """Edit existing message (to remove buttons after approval)."""
        if not self._is_configured():
            return

        try:
            from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
        except ImportError:
            return

        bot = Bot(token=self.bot_token)

        reply_markup = None
        if keyboard:
            reply_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            btn["text"], callback_data=btn["callback_data"]
                        )
                        for btn in row
                    ]
                    for row in keyboard
                ]
            )

        await bot.edit_message_text(
            chat_id=self.chat_id,
            message_id=message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
