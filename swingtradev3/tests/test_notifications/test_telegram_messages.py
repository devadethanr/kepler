from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Bot


class TestTelegramMessages:
    @pytest.mark.asyncio
    async def test_send_briefing_single_string(self):
        from notifications.telegram_client import TelegramClient

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_briefing("Test message")

            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args[1]
            assert call_kwargs["text"] == "Test message"

    @pytest.mark.asyncio
    async def test_send_briefing_multiple_strings(self):
        from notifications.telegram_client import TelegramClient

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_briefing(
                "Line 1",
                "Line 2",
                "Line 3",
            )

            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args[1]
            expected = "Line 1\nLine 2\nLine 3"
            assert call_kwargs["text"] == expected

    @pytest.mark.asyncio
    async def test_send_briefing_no_character_split(self):
        from notifications.telegram_client import TelegramClient

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_briefing(
                "📊 Daily Summary",
                "Positions: 3",
                "P&L: ₹1500.00",
            )

            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args[1]
            text = call_kwargs["text"]

            lines = text.split("\n")
            assert len(lines) == 3
            assert "Positions:" in lines[1]
            assert "P&L:" in lines[2]

    @pytest.mark.asyncio
    async def test_send_entry_alert(self):
        from notifications.telegram_client import TelegramClient

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_entry_alert(
                ticker="INFY",
                company_name="Infosys",
                quantity=10,
                entry_price=1500.0,
                stop_loss=1450.0,
                target=1600.0,
            )

            mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_profit_alert(self):
        from notifications.telegram_client import TelegramClient

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_profit_alert(
                ticker="INFY",
                company_name="Infosys",
                quantity=10,
                entry_price=1500.0,
                exit_price=1600.0,
                pnl_amount=1000.0,
                pnl_percent=6.67,
                exit_reason="Target reached",
            )

            mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_no_setup(self):
        from notifications.telegram_client import TelegramClient

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_no_setup()

            mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_system_status_ok(self):
        from notifications.telegram_client import TelegramClient

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_system_status("All services healthy", is_warning=False)

            mock_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_system_status_warning(self):
        from notifications.telegram_client import TelegramClient

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_system_status("Kite API unhealthy", is_warning=True)

            mock_bot.send_message.assert_called_once()


class TestEventHandlerMessages:
    @pytest.mark.asyncio
    async def test_handle_gtt_triggered_message(self):
        from api.tasks.event_handlers import handle_gtt_triggered

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            from api.tasks.event_bus import BusEvent, EventType

            await handle_gtt_triggered(
                BusEvent(
                    type=EventType.GTT_ALERT,
                    payload={"ticker": "INFY", "trigger_type": "stop", "price": 1500},
                )
            )

            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args[1]
            text = call_kwargs["text"]
            assert "GTT" in text
            assert "INFY" in text

    @pytest.mark.asyncio
    async def test_handle_vix_spike_message(self):
        from api.tasks.event_handlers import handle_vix_spike
        from api.tasks.event_bus import BusEvent, EventType

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            event = BusEvent(
                type=EventType.VIX_SPIKE,
                payload={"vix_level": 25, "action": "tighten_stops"},
            )
            await handle_vix_spike(event)

            mock_bot.send_message.assert_called_once()


class TestSchedulerMessages:
    @pytest.mark.asyncio
    async def test_approval_reminder_message_format(self):
        from notifications.telegram_client import TelegramClient

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_briefing(
                f"⏳ 2 trade(s) awaiting approval.",
                f"📊 Review in dashboard.",
            )

            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args[1]
            text = call_kwargs["text"]
            lines = text.split("\n")
            assert len(lines) == 2
            assert "approval" in lines[0].lower()
            assert "2" in lines[0]
            assert "dashboard" in lines[1].lower()
