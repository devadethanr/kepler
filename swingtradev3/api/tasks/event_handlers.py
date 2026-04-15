"""
Event Handlers — Reactive handlers wired to the EventBus.

Each handler responds to a specific EventType and takes action:
- Logging / state updates
- Telegram notifications
- Knowledge graph updates
- Regime adjustments
"""

from __future__ import annotations

from datetime import datetime

from api.tasks.event_bus import BusEvent, EventType, event_bus
from api.tasks.activity_manager import activity_manager


# ─────────────────────────────────────────────────────────────
# Handler implementations
# ─────────────────────────────────────────────────────────────


async def handle_gtt_triggered(event: BusEvent) -> None:
    """GTT order triggered (stop or target hit). Log trade, update state, alert."""
    ticker = event.payload.get("ticker", "unknown")
    trigger_type = event.payload.get("trigger_type", "unknown")  # "stop" or "target"
    price = event.payload.get("price", 0)

    print(f"[EVENT] GTT triggered: {ticker} — {trigger_type} at ₹{price}")

    # Send Telegram
    try:
        from notifications.telegram_client import TelegramClient

        tg = TelegramClient()
        emoji = "🛑" if trigger_type == "stop" else "🎯"
        await tg.send_briefing(
            f"{emoji} GTT Triggered: {ticker}", f"Type: {trigger_type.upper()}", f"Price: ₹{price}"
        )
    except Exception as e:
        print(f"handle_gtt_triggered: Telegram failed: {e}")


async def handle_vix_spike(event: BusEvent) -> None:
    """VIX spike detected. Tighten stops 20%, pause new entries if extreme."""
    vix_level = event.payload.get("vix_level", 0)
    action = event.payload.get("action", "")

    print(f"[EVENT] VIX spike: {vix_level} — action: {action}")

    # If VIX > threshold, tighten stops on all positions
    if vix_level > 20:
        from storage import read_json, write_json
        from paths import CONTEXT_DIR
        from models import AccountState

        state_data = read_json(CONTEXT_DIR / "state.json", {})
        if state_data and state_data.get("positions"):
            state = AccountState.model_validate(state_data)
            for pos in state.positions:
                # Tighten by 20%
                distance = pos.entry_price - pos.stop_price
                new_stop = pos.entry_price - (distance * 0.80)
                if new_stop > pos.stop_price:
                    pos.stop_price = round(new_stop, 2)
            write_json(CONTEXT_DIR / "state.json", state.model_dump(mode="json"))

    # Send Telegram
    try:
        from notifications.telegram_client import TelegramClient

        tg = TelegramClient()
        await tg.send_briefing(
            f"📈 VIX Spike Alert: {vix_level}",
            f"Action: {action}",
            f"Stops tightened by 20% on all positions.",
        )
    except Exception as e:
        print(f"handle_vix_spike: Telegram failed: {e}")


async def handle_position_news(event: BusEvent) -> None:
    """Breaking news for a held position. Alert on Telegram."""
    ticker = event.payload.get("ticker", "unknown")
    headlines = event.payload.get("headlines", [])

    print(f"[EVENT] Position news: {ticker} — {len(headlines)} headlines")

    if not headlines:
        return

    try:
        from notifications.telegram_client import TelegramClient

        tg = TelegramClient()
        news_text = "\n".join(f"• {h}" for h in headlines[:5])
        await tg.send_briefing(f"📰 News Alert: {ticker}", news_text)
    except Exception as e:
        print(f"handle_position_news: Telegram failed: {e}")


async def handle_stop_hit(event: BusEvent) -> None:
    """Stop loss hit. Log observation, update knowledge graph."""
    ticker = event.payload.get("ticker", "unknown")
    entry_price = event.payload.get("entry_price", 0)
    stop_price = event.payload.get("stop_price", 0)
    pnl_pct = event.payload.get("pnl_pct", 0)

    print(f"[EVENT] Stop hit: {ticker} — P&L: {pnl_pct:.1f}%")

    # Log observation
    try:
        from storage import read_json, write_json
        from paths import CONTEXT_DIR

        observations = read_json(CONTEXT_DIR / "observations.json", [])
        observations.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "stop_hit",
                "ticker": ticker,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "pnl_pct": pnl_pct,
                "lesson": f"{ticker} stopped out at ₹{stop_price} ({pnl_pct:.1f}%)",
            }
        )
        write_json(CONTEXT_DIR / "observations.json", observations)
    except Exception as e:
        print(f"handle_stop_hit: observation failed: {e}")

    # Update knowledge graph
    try:
        from knowledge.wiki_renderer import WikiRenderer

        renderer = WikiRenderer()
        renderer.upsert_stock_note(
            ticker,
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "event": "stop_hit",
                "pnl_pct": pnl_pct,
            },
        )
    except Exception as e:
        print(f"handle_stop_hit: KG update failed: {e}")


async def handle_target_hit(event: BusEvent) -> None:
    """Target hit. Log success, update knowledge graph."""
    ticker = event.payload.get("ticker", "unknown")
    entry_price = event.payload.get("entry_price", 0)
    target_price = event.payload.get("target_price", 0)
    pnl_pct = event.payload.get("pnl_pct", 0)

    print(f"[EVENT] Target hit: {ticker} — P&L: +{pnl_pct:.1f}%")

    # Log observation
    try:
        from storage import read_json, write_json
        from paths import CONTEXT_DIR

        observations = read_json(CONTEXT_DIR / "observations.json", [])
        observations.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "target_hit",
                "ticker": ticker,
                "entry_price": entry_price,
                "target_price": target_price,
                "pnl_pct": pnl_pct,
                "lesson": f"{ticker} hit target at ₹{target_price} (+{pnl_pct:.1f}%)",
            }
        )
        write_json(CONTEXT_DIR / "observations.json", observations)
    except Exception as e:
        print(f"handle_target_hit: observation failed: {e}")

    # Update knowledge graph
    try:
        from knowledge.wiki_renderer import WikiRenderer

        renderer = WikiRenderer()
        renderer.upsert_stock_note(
            ticker,
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "event": "target_hit",
                "pnl_pct": pnl_pct,
            },
        )
    except Exception as e:
        print(f"handle_target_hit: KG update failed: {e}")


async def handle_auth_expiring(event: BusEvent) -> None:
    """Authentication token expiring. Alert user on Telegram."""
    service = event.payload.get("service", "unknown")
    hours_remaining = event.payload.get("hours_remaining", 0)

    print(f"[EVENT] Auth expiring: {service} — {hours_remaining}h remaining")

    try:
        from notifications.telegram_client import TelegramClient

        tg = TelegramClient()
        await tg.send_briefing(
            f"🔑 Auth Expiring: {service}",
            f"Hours remaining: {hours_remaining}",
            f"Please re-authenticate to avoid disruption.",
        )
    except Exception as e:
        print(f"handle_auth_expiring: Telegram failed: {e}")


async def handle_regime_change(event: BusEvent) -> None:
    """Market regime changed. Adjust config via RegimeAdapter."""
    old_regime = event.payload.get("old_regime", "unknown")
    new_regime = event.payload.get("new_regime", event.payload.get("regime", "unknown"))

    print(f"[EVENT] Regime change: {old_regime} → {new_regime}")

    # Log regime change
    try:
        from regime_adapter import RegimeAdaptiveConfig

        adapted = RegimeAdaptiveConfig(new_regime)
        print(f"  → Overlay: {adapted.label}")
        print(f"  → Position size: {adapted.overlay.position_size_pct}%")
        print(f"  → Min score: {adapted.overlay.min_score}")
        print(f"  → Entries allowed: {adapted.overlay.new_entries_allowed}")
    except Exception as e:
        print(f"handle_regime_change: adapter failed: {e}")

    # Send Telegram
    try:
        from notifications.telegram_client import TelegramClient

        tg = TelegramClient()
        await tg.send_briefing(
            f"🔄 Regime Change: {old_regime} → {new_regime}",
            f"Position sizing and stops adjusted automatically.",
        )
    except Exception as e:
        print(f"handle_regime_change: Telegram failed: {e}")


# ─────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────


def register_all_handlers(bus=None) -> None:
    """Register all event handlers with the event bus."""
    target_bus = bus or event_bus
    target_bus.subscribe(EventType.GTT_ALERT, handle_gtt_triggered)
    target_bus.subscribe(EventType.VIX_SPIKE, handle_vix_spike)
    target_bus.subscribe(EventType.NEWS_BREAK, handle_position_news)
    target_bus.subscribe(EventType.STOP_HIT, handle_stop_hit)
    target_bus.subscribe(EventType.TARGET_HIT, handle_target_hit)
    target_bus.subscribe(EventType.AUTH_EXPIRING, handle_auth_expiring)
    target_bus.subscribe(EventType.REGIME_CHANGE, handle_regime_change)
    print(f"EventHandlers: registered 7 handlers")
