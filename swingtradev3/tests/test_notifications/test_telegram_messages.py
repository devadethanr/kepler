from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


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

    @pytest.mark.asyncio
    async def test_send_text_truncates_overlong_messages(self):
        from notifications.telegram_client import TelegramClient, TELEGRAM_SAFE_TEXT_LIMIT

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            tg = TelegramClient()
            await tg.send_text("x" * (TELEGRAM_SAFE_TEXT_LIMIT + 500))

            call_kwargs = mock_bot.send_message.call_args[1]
            assert len(call_kwargs["text"]) <= TELEGRAM_SAFE_TEXT_LIMIT
            assert "[truncated]" in call_kwargs["text"]


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
    async def test_handle_position_news_formats_headline_dicts(self):
        from api.tasks.event_bus import BusEvent, EventType
        from api.tasks.event_handlers import handle_position_news

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            await handle_position_news(
                BusEvent(
                    type=EventType.NEWS_BREAK,
                    payload={
                        "ticker": "RELIANCE",
                        "headlines": [
                            {
                                "title": "Reliance Industries Q4 profit beats estimates",
                                "content": "x" * 1200,
                                "url": "https://www.reuters.com/markets/reliance",
                                "published_at": "2026-05-05T10:00:00+00:00",
                            }
                        ],
                    },
                )
            )

            text = mock_bot.send_message.call_args[1]["text"]
            assert "Reliance Industries Q4 profit" in text
            assert "https://www.reuters.com/markets/reliance" in text
            assert "'content':" not in text
            assert len(text) < 1000

    @pytest.mark.asyncio
    async def test_handle_market_news_digest_groups_tickers_and_general_items(self):
        from api.tasks.event_bus import BusEvent, EventType
        from api.tasks.event_handlers import handle_market_news_digest

        with patch("telegram.Bot") as mock_bot_class:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_class.return_value = mock_bot

            await handle_market_news_digest(
                BusEvent(
                    type=EventType.MARKET_NEWS_DIGEST,
                    payload={
                        "ticker_groups": [
                            {
                                "ticker": "RELIANCE",
                                "company_name": "Reliance Industries",
                                "items": [
                                    {
                                        "title": "Reliance Industries Q4 profit beats estimates",
                                        "url": "https://www.reuters.com/markets/reliance",
                                    }
                                ],
                            }
                        ],
                        "general": [
                            {
                                "title": "RBI policy keeps market cautious",
                                "url": "https://example.com/rbi-policy",
                            }
                        ],
                        "item_count": 2,
                    },
                )
            )

            text = mock_bot.send_message.call_args[1]["text"]
            assert "Market News Digest" in text
            assert "RELIANCE" in text
            assert "Reliance Industries Q4 profit" in text
            assert "General / Macro" in text
            assert "RBI policy" in text

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
                "⏳ 2 trade(s) awaiting approval.",
                "📊 Review in dashboard.",
            )

            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args[1]
            text = call_kwargs["text"]
            lines = text.split("\n")
            assert len(lines) == 2
            assert "approval" in lines[0].lower()
            assert "2" in lines[0]
            assert "dashboard" in lines[1].lower()
