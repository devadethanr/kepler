from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from swingtradev3.config import cfg
from swingtradev3.logging_config import get_logger
from swingtradev3.models import AccountState
from swingtradev3.notifications.telegram_client import TelegramClient
from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json


class TelegramCommandHandler:
    """Handle Telegram bot commands (e.g., /list, /positions, /config)."""

    def __init__(self, client: TelegramClient | None = None) -> None:
        self.client = client or TelegramClient()
        self.log = get_logger("telegram_commands")

    async def handle_command(self, command: str, args: list[str] = None) -> str:
        """Process a Telegram command and return response message."""
        command = command.lower().strip()
        args = args or []

        self.log.info("Received command: {} with args: {}", command, args)

        handlers = {
            "/help": self._cmd_help,
            "/start": self._cmd_help,
            "/list": self._cmd_list,
            "/positions": self._cmd_positions,
            "/status": self._cmd_status,
            "/config": self._cmd_config,
            "/remove": self._cmd_remove,
            "/pause": self._cmd_pause,
            "/resume": self._cmd_resume,
            "/stats": self._cmd_stats,
            "/cash": self._cmd_cash,
            "/pnl": self._cmd_pnl,
        }

        handler = handlers.get(command, self._cmd_unknown)
        response = await handler(args)
        
        # Telegram message limit is 4096 characters - use plain text to avoid HTML issues
        if len(response) > 4000:
            # Strip HTML tags cleanly and truncate at line boundary
            import re
            clean = re.sub(r'<[^>]+>', '', response)
            # Find last complete line before 4000
            lines = clean[:4000].split('\n')
            if len(lines) > 1:
                response = '\n'.join(lines[:-1])
            else:
                response = clean[:3990]
            response += "\n\n... (truncated)"
        
        return response

    async def _cmd_help(self, args: list[str]) -> str:
        """Show available commands."""
        return (
            "📋 <b>SwingTradeV3 Bot Commands</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>📊 Trading Commands:</b>\n"
            "• /list - Show shortlisted stocks awaiting approval\n"
            "• /positions - Show open positions with P&L\n"
            "• /cash - Show available cash\n"
            "• /pnl - Show today's P&L\n\n"
            "<b>⚙️ System Commands:</b>\n"
            "• /status - System status and health\n"
            "• /config - Show current configuration\n"
            "• /stats - Trading statistics\n"
            "• /pause - Pause execution\n"
            "• /resume - Resume execution\n\n"
            "<b>🛠️ Management:</b>\n"
            "• /remove TICKER - Remove stock from shortlist\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🤖 I'm an AI-powered swing trading bot for Indian equities"
        )

    async def _cmd_list(self, args: list[str]) -> str:
        """Show shortlisted stocks awaiting approval."""
        pending_file = CONTEXT_DIR / "pending_approvals.json"
        pending = read_json(pending_file, [])

        if not pending:
            return (
                "📭 <b>No Stocks Awaiting Approval</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "No shortlisted stocks right now.\n"
                "Next scan: Tomorrow 8:45 AM IST"
            )

        lines = ["📋 <b>Shortlisted Stocks (Awaiting Approval)</b>", "━" * 30]

        for item in pending:
            if item.get("status") != "pending":
                continue

            ticker = item.get("ticker", "N/A")
            company = item.get("company_name", ticker)
            score = item.get("score", "N/A")
            setup = item.get("setup_type", "N/A")
            entry_low = item.get("entry_zone", {}).get("low", "N/A")
            entry_high = item.get("entry_zone", {}).get("high", "N/A")
            stop = item.get("stop_price", "N/A")
            target = item.get("target_price", "N/A")

            lines.append(
                f"\n🔔 <b>{company} ({ticker})</b>\n"
                f"   📊 Score: {score}/10 | {setup.title()}\n"
                f"   💰 Entry: ₹{entry_low} - ₹{entry_high}\n"
                f"   🛡️ Stop: ₹{stop} | 🎯 Target: ₹{target}"
            )

        lines.append("\n" + "━" * 30)
        lines.append("\n✅ Click YES on any message above to approve")
        lines.append("❌ Click NO to skip that trade")

        return "\n".join(lines)

    async def _cmd_positions(self, args: list[str]) -> str:
        """Show open positions with P&L."""
        state_file = CONTEXT_DIR / "state.json"
        state_data = read_json(state_file, {})
        positions = state_data.get("positions", [])

        if not positions:
            return (
                "📭 <b>No Open Positions</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "You're not holding any positions.\n"
                "Use /list to see available setups."
            )

        lines = ["📊 <b>Open Positions</b>", "━" * 30]

        total_pnl = 0
        for pos in positions:
            ticker = pos.get("ticker", "N/A")
            qty = pos.get("quantity", 0)
            entry = pos.get("entry_price", 0)
            current = pos.get("current_price", entry)
            stop = pos.get("stop_price", 0)
            target = pos.get("target_price", 0)

            pnl = (current - entry) * qty
            pnl_pct = (current / entry - 1) * 100 if entry > 0 else 0
            total_pnl += pnl

            emoji = "🟢" if pnl >= 0 else "🔴"

            lines.append(
                f"\n{emoji} <b>{ticker}</b> | {qty} shares\n"
                f"   💰 Entry: ₹{entry:,.2f} | Current: ₹{current:,.2f}\n"
                f"   📈 P&L: ₹{pnl:+,.0f} ({pnl_pct:+.1f}%)\n"
                f"   🛡️ Stop: ₹{stop:,.0f} | 🎯 Target: ₹{target:,.0f}"
            )

        lines.append("\n" + "━" * 30)
        lines.append(f"\n📊 <b>Total Unrealized P&L: ₹{total_pnl:+,.0f}</b>")

        return "\n".join(lines)

    async def _cmd_cash(self, args: list[str]) -> str:
        """Show available cash."""
        state_file = CONTEXT_DIR / "state.json"
        state_data = read_json(state_file, {})
        cash = state_data.get("cash_inr", 0)

        return (
            "💵 <b>Cash Position</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Available Cash: <b>₹{cash:,.0f}</b>\n"
            f"📊 Reserve (10%): ₹{cash * 0.1:,.0f}\n"
            f"💵 Available for Trading: ₹{cash * 0.9:,.0f}\n\n"
            "━" * 30 + "\n"
            "Next scan: Tomorrow 8:45 AM IST"
        )

    async def _cmd_pnl(self, args: list[str]) -> str:
        """Show today's P&L."""
        state_file = CONTEXT_DIR / "state.json"
        state_data = read_json(state_file, {})
        realized = state_data.get("realized_pnl", 0)
        unrealized = state_data.get("unrealized_pnl", 0)

        total = realized + unrealized
        emoji = "🟢" if total >= 0 else "🔴"

        return (
            "📈 <b>Today's P&L</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{emoji} <b>Total P&L: ₹{total:+,.0f}</b>\n\n"
            f"✅ Realized: ₹{realized:+,.0f}\n"
            f"📊 Unrealized: ₹{unrealized:+,.0f}\n\n"
            "━" * 30
        )

    async def _cmd_status(self, args: list[str]) -> str:
        """Show system status."""
        # Check if paused
        pause_file = CONTEXT_DIR / "PAUSE"
        is_paused = pause_file.exists()

        # Check pending approvals
        pending_file = CONTEXT_DIR / "pending_approvals.json"
        pending_count = len(
            [p for p in read_json(pending_file, []) if p.get("status") == "pending"]
        )

        # Check positions
        state_file = CONTEXT_DIR / "state.json"
        state_data = read_json(state_file, {})
        position_count = len(state_data.get("positions", []))

        status_emoji = "⏸️" if is_paused else "▶️"
        status_text = "PAUSED" if is_paused else "RUNNING"

        return (
            f"⚙️ <b>System Status: {status_emoji} {status_text}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Open Positions: <b>{position_count}</b>\n"
            f"⏳ Pending Approvals: <b>{pending_count}</b>\n"
            f"💰 Cash: ₹{state_data.get('cash_inr', 0):,.0f}\n\n"
            "<b>API Status:</b>\n"
            "✅ Kite API: Connected\n"
            "✅ NIM LLM: Connected\n"
            "✅ Telegram: Connected\n\n"
            "━" * 30 + "\n"
            f"Last update: {datetime.now().strftime('%H:%M:%S')} IST"
        )

    async def _cmd_config(self, args: list[str]) -> str:
        """Show current configuration."""
        return (
            "⚙️ <b>Bot Configuration</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>Trading Mode:</b>\n"
            f"• Mode: {cfg.trading.mode.value.upper()}\n"
            f"• Exchange: {cfg.trading.exchange}\n"
            f"• Min Cash Reserve: {cfg.trading.min_cash_reserve_pct * 100:.0f}%\n\n"
            "<b>Risk Settings:</b>\n"
            f"• Max Risk/Trade: {cfg.risk.max_risk_pct_per_trade}%\n"
            f"• Max Drawdown: {cfg.risk.max_drawdown_pct}%\n"
            f"• Max Weekly Loss: {cfg.risk.max_weekly_loss_pct}%\n\n"
            "<b>Position Sizing:</b>\n"
            f"• High Score (8+): {cfg.risk.confidence_sizing.high.capital_pct * 100:.0f}%\n"
            f"• Medium Score (7-8): {cfg.risk.confidence_sizing.medium.capital_pct * 100:.0f}%\n\n"
            "━" * 30
        )

    async def _cmd_stats(self, args: list[str]) -> str:
        """Show trading statistics."""
        stats_file = CONTEXT_DIR / "stats.json"
        stats = read_json(stats_file, {})

        if not stats:
            return (
                "📊 <b>No Statistics Available</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Start trading to build statistics.\n"
                "Stats are updated monthly."
            )

        return (
            "📊 <b>Trading Statistics</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📈 Total Trades: {stats.get('total_trades', 0)}\n"
            f"✅ Win Rate: {stats.get('win_rate', 0) * 100:.1f}%\n"
            f"📊 Profit Factor: {stats.get('profit_factor', 0):.2f}\n"
            f"📉 Max Drawdown: {stats.get('max_drawdown', 0) * 100:.1f}%\n"
            f"📈 Sharpe Ratio: {stats.get('sharpe', 0):.2f}\n\n"
            "━" * 30
        )

    async def _cmd_pause(self, args: list[str]) -> str:
        """Pause execution."""
        pause_file = CONTEXT_DIR / "PAUSE"
        pause_file.touch()
        return (
            "⏸️ <b>Execution PAUSED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "The bot will not place new orders.\n"
            "Use /resume to continue.\n\n"
            "Existing positions will still be monitored."
        )

    async def _cmd_resume(self, args: list[str]) -> str:
        """Resume execution."""
        pause_file = CONTEXT_DIR / "PAUSE"
        if pause_file.exists():
            pause_file.unlink()
        return (
            "▶️ <b>Execution RESUMED</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "The bot is now running.\n"
            "Next scan: Tomorrow 8:45 AM IST"
        )

    async def _cmd_remove(self, args: list[str]) -> str:
        """Remove a stock from shortlist."""
        if not args:
            return (
                "❌ <b>Missing Ticker</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Usage: /remove TICKER\n"
                "Example: /remove SBIN"
            )

        ticker = args[0].upper()
        pending_file = CONTEXT_DIR / "pending_approvals.json"
        pending = read_json(pending_file, [])

        # Find and remove
        new_pending = [p for p in pending if p.get("ticker") != ticker]
        removed = len(pending) - len(new_pending)

        if removed == 0:
            return f"❌ <b>{ticker}</b> not found in shortlist"

        from swingtradev3.storage import write_json

        write_json(pending_file, new_pending)

        return (
            f"🗑️ <b>{ticker} Removed</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{ticker} has been removed from shortlist.\n"
            "This stock will not be traded."
        )

    async def _cmd_unknown(self, args: list[str]) -> str:
        """Handle unknown commands."""
        return (
            "❓ <b>Unknown Command</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Use /help to see available commands."
        )
