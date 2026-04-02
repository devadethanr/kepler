from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from swingtradev3.logging_config import get_logger
from swingtradev3.models import PendingApproval
from swingtradev3.notifications.telegram_client import TelegramClient
from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json


class TelegramHandler:
    """Original handler for managing pending approvals."""

    def __init__(self) -> None:
        self.path = CONTEXT_DIR / "pending_approvals.json"

    def _load(self) -> list[PendingApproval]:
        return [
            PendingApproval.model_validate(item) for item in read_json(self.path, [])
        ]

    def _save(self, approvals: list[PendingApproval]) -> None:
        write_json(self.path, [item.model_dump(mode="json") for item in approvals])

    def record_approval(self, ticker: str, approved: bool) -> None:
        approvals = self._load()
        for item in approvals:
            if item.ticker == ticker:
                item.approved = approved
        self._save(approvals)

    def expire_stale(self, now: datetime | None = None) -> list[str]:
        now = now or datetime.utcnow()
        approvals = self._load()
        expired = [item.ticker for item in approvals if item.expires_at <= now]
        approvals = [item for item in approvals if item.expires_at > now]
        self._save(approvals)
        return expired

    @staticmethod
    def build_expiry(created_at: datetime, timeout_hours: int) -> datetime:
        return created_at + timedelta(hours=timeout_hours)


class TelegramInboundHandler:
    """Handle incoming Telegram messages and callbacks (YES/NO approvals)."""

    LAST_UPDATE_ID_FILE = CONTEXT_DIR / "telegram_last_update_id.json"
    PROCESSED_UPDATES_FILE = CONTEXT_DIR / "telegram_processed_ids.json"
    MAX_PROCESSED_IDS = 1000

    def __init__(self, client: TelegramClient | None = None, force_from_zero: bool = False) -> None:
        self.client = client or TelegramClient()
        self.log = get_logger("telegram_inbound")
        self.pending_file = CONTEXT_DIR / "pending_approvals.json"
        self.last_update_id = 0 if force_from_zero else self._load_last_update_id()
        self._processed_updates: set[int] = set() if force_from_zero else self._load_processed_ids()

    def _load_processed_ids(self) -> set[int]:
        """Load processed update IDs from persistent storage."""
        try:
            data = read_json(self.PROCESSED_UPDATES_FILE, {"ids": []})
            return set(data.get("ids", []))
        except Exception:
            return set()

    def _save_processed_ids(self) -> None:
        """Persist processed update IDs to disk."""
        try:
            ids_list = sorted(list(self._processed_updates))[-self.MAX_PROCESSED_IDS:]
            write_json(self.PROCESSED_UPDATES_FILE, {"ids": ids_list})
        except Exception as e:
            self.log.warning("Failed to save processed IDs: {}", e)

    def _load_last_update_id(self) -> int:
        """Load the last processed update_id from disk."""
        try:
            data = read_json(self.LAST_UPDATE_ID_FILE, {})
            return data.get("last_update_id", 0)
        except Exception:
            return 0

    def _save_last_update_id(self) -> None:
        """Persist the last processed update_id to disk."""
        try:
            write_json(
                self.LAST_UPDATE_ID_FILE,
                {
                    "last_update_id": self.last_update_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        except Exception as e:
            self.log.warning("Failed to save last_update_id: {}", e)

    async def start_polling(self, interval: int = 5) -> None:
        """Start polling for updates."""
        self.log.info("Starting Telegram inbound polling...")
        self.log.info("Starting from update_id: {} (processed count: {})", 
                     self.last_update_id, len(self._processed_updates))
        loop_count = 0
        while True:
            loop_count += 1
            try:
                self.log.info("Loop {}: Calling get_updates with offset={}", 
                            loop_count, self.last_update_id + 1)
                updates = await self.client.get_updates(
                    offset=self.last_update_id + 1,
                    limit=100,
                )
                self.log.info("Loop {}: Got {} updates", loop_count, len(updates))
                if updates:
                    self.log.debug("Received {} updates", len(updates))
                    for update in updates:
                        update_id = update.get("update_id", 0)
                        # Skip if already processed (deduplication guard)
                        if (
                            update_id <= self.last_update_id
                            or update_id in self._processed_updates
                        ):
                            self.log.debug(
                                "Skipping already processed update_id: {}", update_id
                            )
                            continue
                        await self._process_update(update)
                        self._processed_updates.add(update_id)
                        if update_id > self.last_update_id:
                            self.last_update_id = update_id
                        # Save immediately to prevent duplicates on restart
                        self._save_processed_ids()
                    # Persist last_update_id after batch
                    self._save_last_update_id()
            except Exception as e:
                self.log.error("Error polling Telegram: {}", e)

            await asyncio.sleep(interval)

    async def _process_update(self, update: dict[str, Any]) -> None:
        """Process a single update (button click or text message)."""
        callback = update.get("callback_query")
        message = update.get("message")
        
        # Get update_id for logging
        update_id = update.get("update_id", "unknown")
        self.log.info("Processing update_id: {}", update_id)

        # Handle button clicks (approvals)
        if callback:
            data = callback.get("data", "")
            callback_id = callback.get("id")
            message_id = callback.get("message_id")

            if data.startswith("APPROVE:"):
                ticker = data.split(":", 1)[1]
                await self._handle_approval(ticker, True, callback_id, message_id)
            elif data.startswith("REJECT:"):
                ticker = data.split(":", 1)[1]
                await self._handle_approval(ticker, False, callback_id, message_id)

        # Handle text commands
        elif message and message.get("text", "").startswith("/"):
            text = message.get("text", "").strip()
            parts = text.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            # Process command
            from swingtradev3.notifications.telegram_commands import (
                TelegramCommandHandler,
            )

            handler = TelegramCommandHandler(self.client)
            response = await handler.handle_command(command, args)

            # Send response - log EXACTLY what we're sending
            self.log.info("Sending {} response (update_id: {}, text length: {})", 
                         command, update_id, len(response))
            self.log.info("Response preview: {}", response[:200])
            await self.client.send_text(response)
            self.log.info(
                "Completed command: {} (update_id: {})", command, update_id
            )

    async def _handle_approval(
        self,
        ticker: str,
        approved: bool,
        callback_id: str,
        message_id: int | None,
    ) -> None:
        """Handle YES/NO approval from user."""
        action = "APPROVED" if approved else "REJECTED"
        self.log.info("User {} trade for {}", action, ticker)

        # Check if already processed (prevent duplicates)
        if self._is_already_processed(ticker):
            self.log.warning(
                "Trade {} already processed, ignoring duplicate click", ticker
            )
            await self.client.answer_callback_query(
                callback_id,
                f"⚠️ {ticker} already {action.lower()} - check messages above",
            )
            return

        # Get trade details
        trade_details = self._get_trade_details(ticker)

        # Acknowledge immediately
        ack_text = f"✅ {ticker} APPROVED" if approved else f"❌ {ticker} REJECTED"
        try:
            await self.client.answer_callback_query(callback_id, ack_text)
        except Exception as e:
            self.log.warning("Popup acknowledgment failed (may be old): {}", e)

        # Update pending file
        self._update_pending_approval(ticker, approved)

        # Send NEW confirmation message instead of editing
        confirmation_msg = self._build_confirmation_message(
            ticker, approved, trade_details
        )
        try:
            await self.client.send_text(confirmation_msg)
            self.log.info("Sent confirmation for {}", ticker)
        except Exception as e:
            self.log.error("Failed to send confirmation: {}", e)

    def _is_already_processed(self, ticker: str) -> bool:
        """Check if this ticker was already approved/rejected."""
        try:
            data = read_json(self.pending_file, [])
            for item in data:
                if item.get("ticker") == ticker:
                    status = item.get("status", "pending")
                    return status in ["approved", "rejected"]
            return False
        except Exception:
            return False

    def _build_confirmation_message(
        self, ticker: str, approved: bool, details: dict[str, Any]
    ) -> str:
        """Build confirmation message sent after approval/rejection."""
        company = details.get("company_name", ticker)
        score = details.get("score", "N/A")
        setup = details.get("setup_type", "N/A")
        entry_low = details.get("entry_zone", {}).get("low", "N/A")
        entry_high = details.get("entry_zone", {}).get("high", "N/A")
        stop = details.get("stop_price", "N/A")
        target = details.get("target_price", "N/A")

        if approved:
            return (
                f"✅ <b>{company} ({ticker}) - APPROVED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Status: <b>APPROVED by you</b>\n"
                f"📊 Score: {score}/10 | {setup}\n"
                f"💰 Entry: ₹{entry_low} - ₹{entry_high}\n"
                f"🛡️ Stop: ₹{stop} | 🎯 Target: ₹{target}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 Will execute at next market open (9:15 AM IST)\n"
                f"🔔 You'll receive an alert when position is entered"
            )
        else:
            return (
                f"❌ <b>{company} ({ticker}) - REJECTED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"❌ Status: <b>REJECTED by you</b>\n"
                f"📊 Score: {score}/10 | {setup}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 Setup skipped\n"
                f"🔔 Next scan: Tomorrow 8:45 AM IST"
            )

    def _get_trade_details(self, ticker: str) -> dict[str, Any]:
        """Get trade details from pending approvals."""
        if not self.pending_file.exists():
            return {}

        try:
            approvals = read_json(self.pending_file, [])
            for item in approvals:
                if item.get("ticker") == ticker:
                    return item
            return {}
        except Exception:
            return {}

    def _build_approval_message(self, ticker: str, details: dict[str, Any]) -> str:
        """Build detailed approval acknowledgment message."""
        entry_low = details.get("entry_zone", {}).get("low", "N/A")
        entry_high = details.get("entry_zone", {}).get("high", "N/A")
        stop = details.get("stop_price", "N/A")
        target = details.get("target_price", "N/A")

        return (
            f"✅ Trade APPROVED for {ticker}\n"
            f"📊 Entry: ₹{entry_low} - ₹{entry_high}\n"
            f"🛡️ Stop: ₹{stop} | 🎯 Target: ₹{target}\n"
            f"⏰ Will execute at next market open"
        )

    def _build_rejection_message(self, ticker: str, details: dict[str, Any]) -> str:
        """Build detailed rejection acknowledgment message."""
        return (
            f"❌ Trade REJECTED for {ticker}\n"
            f"This setup will be skipped.\n"
            f"Next scan: Tomorrow 8:45 AM"
        )

    def _build_detailed_status_message(
        self, ticker: str, approved: bool, details: dict[str, Any]
    ) -> str:
        """Build detailed status message for Telegram."""
        company_name = details.get("company_name", ticker)
        score = details.get("score", "N/A")
        setup_type = details.get("setup_type", "N/A")
        entry_low = details.get("entry_zone", {}).get("low", "N/A")
        entry_high = details.get("entry_zone", {}).get("high", "N/A")
        stop = details.get("stop_price", "N/A")
        target = details.get("target_price", "N/A")
        holding_days = details.get("holding_days_expected", "N/A")

        if approved:
            return (
                f"🟢 <b>{company_name} ({ticker}) - APPROVED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ <b>Status:</b> APPROVED by you\n"
                f"📊 <b>Score:</b> {score}/10 | {setup_type}\n"
                f"💰 <b>Entry Zone:</b> ₹{entry_low} - ₹{entry_high}\n"
                f"🛡️ <b>Stop Loss:</b> ₹{stop}\n"
                f"🎯 <b>Target:</b> ₹{target}\n"
                f"⏰ <b>Hold:</b> ~{holding_days} days\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 <b>Next Steps:</b>\n"
                f"• Order will be placed at next market open (9:15 AM IST)\n"
                f"• GTT stop-loss will be set automatically\n"
                f"• You'll get an alert when position is entered\n"
                f"• Monitor Telegram for updates"
            )
        else:
            return (
                f"🔴 <b>{company_name} ({ticker}) - REJECTED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"❌ <b>Status:</b> REJECTED by you\n"
                f"📊 <b>Score:</b> {score}/10 | {setup_type}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 <b>What happens next:</b>\n"
                f"• This trade setup is skipped\n"
                f"• No order will be placed\n"
                f"• Next scan: Tomorrow 8:45 AM IST\n"
                f"• Check briefing for other setups"
            )

    def _update_pending_approval(self, ticker: str, approved: bool) -> None:
        """Update the pending approvals JSON file."""
        if not self.pending_file.exists():
            self.log.warning("No pending approvals file found")
            return

        try:
            approvals = read_json(self.pending_file, [])

            # Find and update the approval
            for item in approvals:
                if item.get("ticker") == ticker:
                    item["approved"] = approved
                    item["approved_at"] = datetime.now().isoformat()
                    item["status"] = "approved" if approved else "rejected"
                    break

            write_json(self.pending_file, approvals)

            self.log.info("Updated pending approval for {}", ticker)
        except Exception as e:
            self.log.error("Error updating pending approvals: {}", e)

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Get list of pending approvals."""
        if not self.pending_file.exists():
            return []

        try:
            data = read_json(self.pending_file, [])
            return [item for item in data if item.get("status") == "pending"]
        except Exception as e:
            self.log.error("Error reading pending approvals: {}", e)
            return []

    def add_pending_approval(self, approval: dict[str, Any]) -> int | None:
        """Add a new pending approval and return message_id."""
        try:
            data = read_json(self.pending_file, [])

            approval["status"] = "pending"
            approval["created_at"] = datetime.now().isoformat()
            data.append(approval)

            write_json(self.pending_file, data)

            self.log.info("Added pending approval for {}", approval.get("ticker"))
            return approval.get("message_id")
        except Exception as e:
            self.log.error("Error adding pending approval: {}", e)
            return None
