from __future__ import annotations

from typing import Any


class NotificationFormatter:
    @staticmethod
    def entry_alert(
        ticker: str,
        company_name: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
    ) -> str:
        return (
            f"🟢 {company_name} ({ticker}) - ENTRY FILLED\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Quantity: {quantity} shares\n"
            f"💰 Entry: ₹{entry_price:,.2f}\n"
            f"🛡️ Stop Loss: ₹{stop_loss:,.2f}\n"
            f"🎯 Target: ₹{target:,.2f}\n"
            f"📈 Risk: ₹{entry_price - stop_loss:,.2f} per share"
        )

    @staticmethod
    def profit_alert(
        ticker: str,
        company_name: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        pnl_amount: float,
        pnl_percent: float,
        exit_reason: str,
    ) -> str:
        emoji = "💚" if pnl_amount >= 0 else "❤️"
        sign = "+" if pnl_amount >= 0 else ""

        reason_map = {
            "target": "🎯 Target Hit",
            "stop": "🛡️ Stop Loss",
            "trailing_stop": "⛔ Trailing Stop",
            "manual": "👤 Manual Exit",
        }
        reason_text = reason_map.get(exit_reason, exit_reason)

        return (
            f"{emoji} {company_name} ({ticker}) - TRADE CLOSED\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 {quantity} shares @ ₹{exit_price:,.2f}\n"
            f"💵 P&L: ₹{pnl_amount:+,.0f} ({pnl_percent:+.1f}%)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔔 Reason: {reason_text}\n"
            f"📈 Entry was: ₹{entry_price:,.2f}"
        )

    @staticmethod
    def approval_request(
        ticker: str,
        company_name: str,
        score: float,
        setup_type: str,
        entry_zone_low: float,
        entry_zone_high: float,
        stop_loss: float,
        target: float,
        holding_days: int,
        reasoning: str,
    ) -> str:
        setup_emoji = {
            "breakout": "🚀",
            "pullback": "📉",
            "earnings_play": "📊",
            "sector_rotation": "🔄",
        }.get(setup_type, "📈")

        return (
            f"🔔 NEW TRADE SETUP\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{setup_emoji} {company_name} ({ticker})\n"
            f"📊 Score: {score:.1f}/10 | {setup_type.title()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Entry Zone: ₹{entry_zone_low:,.0f} - ₹{entry_zone_high:,.0f}\n"
            f"🛡️ Stop Loss: ₹{stop_loss:,.0f}\n"
            f"🎯 Target: ₹{target:,.0f}\n"
            f"⏰ Hold: ~{holding_days} days\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Why: {reasoning[:100]}..."
        )

    @staticmethod
    def daily_summary(
        positions_count: int,
        pending_count: int,
        cash: float,
        unrealized_pnl: float,
        realized_pnl: float,
    ) -> str:
        pnl_emoji = "📈" if unrealized_pnl >= 0 else "📉"

        return (
            f"📊 DAILY SUMMARY\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"� open Positions: {positions_count}\n"
            f"⏳ Pending Approvals: {pending_count}\n"
            f"💵 Cash Available: ₹{cash:,.0f}\n"
            f"{pnl_emoji} Today's P&L: ₹{unrealized_pnl:+,.0f}\n"
            f"✅ Realized P&L: ₹{realized_pnl:+,.0f}"
        )

    @staticmethod
    def system_status(message: str, is_warning: bool = False) -> str:
        emoji = "⚠️" if is_warning else "ℹ️"
        return f"{emoji} SYSTEM: {message}"

    @staticmethod
    def no_setup_alert() -> str:
        return (
            f"📭 No Trade Setups Today\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"No stocks met the criteria today.\n"
            f"Will scan again tomorrow."
        )
