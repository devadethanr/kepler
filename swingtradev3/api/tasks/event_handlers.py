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
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from api.tasks.event_bus import BusEvent, EventType, event_bus
from config import cfg

IST = ZoneInfo("Asia/Kolkata")


# ─────────────────────────────────────────────────────────────
# Handler implementations
# ─────────────────────────────────────────────────────────────

def _headline_domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _format_headline(item: Any) -> str | None:
    if isinstance(item, str):
        text = item.strip()
        return f"• {text[:220]}" if text else None
    if not isinstance(item, dict):
        return None
    title = str(item.get("title") or item.get("content") or "").strip()
    url = str(item.get("url") or "").strip()
    if not title and not url:
        return None
    if len(title) > 180:
        title = f"{title[:177]}..."
    domain = str(item.get("domain") or _headline_domain(url) or "").strip()
    published = str(
        item.get("published_at_ist")
        or item.get("published_at")
        or item.get("fetched_at_ist")
        or ""
    ).strip()
    source_type = str(item.get("source_type") or "").strip()
    label = "official" if source_type in {"official_filing", "regulator", "broker_api"} else ""
    if source_type == "publisher_rss":
        label = "publisher"
    if source_type == "crawler":
        label = "crawler"
    confidence = item.get("confidence")
    confidence_text = (
        f"conf={float(confidence):.2f}" if isinstance(confidence, (int, float)) else ""
    )
    meta = " | ".join(part for part in (domain, label, confidence_text, published) if part)
    suffix = f" ({meta})" if meta else ""
    if url:
        return f"• {title}{suffix}\n  {url}"
    return f"• {title}{suffix}"


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
        alert_limit = int(cfg.research.filter.news_position_alert_max_items)
        lines = [
            line for line in (_format_headline(item) for item in headlines[:alert_limit]) if line
        ]
        if not lines:
            return
        news_text = "\n".join(lines)
        await tg.send_briefing(f"📰 News Alert: {ticker}", news_text)
    except Exception as e:
        print(f"handle_position_news: Telegram failed: {e}")


async def handle_market_news_digest(event: BusEvent) -> None:
    """General market news digest, grouped by detected stock where possible."""
    ticker_groups = event.payload.get("ticker_groups", [])
    general = event.payload.get("general", [])
    item_count = int(event.payload.get("item_count") or 0)

    print(
        f"[EVENT] Market news digest: {len(ticker_groups)} ticker groups, "
        f"{len(general)} general items"
    )

    if not item_count:
        return

    sections: list[str] = []
    filter_cfg = cfg.research.filter
    max_groups = int(filter_cfg.market_news_digest_max_ticker_groups)
    max_per_ticker = int(filter_cfg.market_news_digest_max_items_per_ticker)
    max_general = int(filter_cfg.market_news_digest_max_general_items)

    for group in ticker_groups[:max_groups]:
        if not isinstance(group, dict):
            continue
        ticker = str(group.get("ticker") or "UNKNOWN").upper()
        company = str(group.get("company_name") or ticker).strip()
        lines = [
            line
            for line in (_format_headline(item) for item in group.get("items", [])[:max_per_ticker])
            if line
        ]
        if lines:
            sections.append(f"📌 {ticker} — {company}\n" + "\n".join(lines))

    general_lines = [
        line for line in (_format_headline(item) for item in general[:max_general]) if line
    ]
    if general_lines:
        sections.append("🌐 General / Macro\n" + "\n".join(general_lines))

    if not sections:
        return

    try:
        from notifications.telegram_client import TelegramClient

        tg = TelegramClient()
        await tg.send_briefing("🗞️ Market News Digest", "\n\n".join(sections))
    except Exception as e:
        print(f"handle_market_news_digest: Telegram failed: {e}")


async def handle_stop_hit(event: BusEvent) -> None:
    """Stop loss hit. Log observation, update knowledge graph."""
    ticker = event.payload.get("ticker", "unknown")
    entry_price = event.payload.get("entry_price", 0)
    stop_price = event.payload.get("stop_price", 0)
    pnl_pct = event.payload.get("pnl_pct", 0)

    print(f"[EVENT] Stop hit: {ticker} — P&L: {pnl_pct:.1f}%")

    try:
        from context_graph.repository import ContextGraphRepository

        repo = ContextGraphRepository()
        repo.record_observation(
            observation_type="stop_hit",
            ticker=str(ticker),
            payload={
                "timestamp": datetime.now(IST).isoformat(),
                "type": "stop_hit",
                "ticker": ticker,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "pnl_pct": pnl_pct,
                "lesson": f"{ticker} stopped out at Rs {stop_price} ({pnl_pct:.1f}%)",
            },
            source="event_handler:stop_hit",
        )
        repo.close()
    except Exception as e:
        print(f"handle_stop_hit: observation failed: {e}")


async def handle_target_hit(event: BusEvent) -> None:
    """Target hit. Log success, update knowledge graph."""
    ticker = event.payload.get("ticker", "unknown")
    entry_price = event.payload.get("entry_price", 0)
    target_price = event.payload.get("target_price", 0)
    pnl_pct = event.payload.get("pnl_pct", 0)

    print(f"[EVENT] Target hit: {ticker} — P&L: +{pnl_pct:.1f}%")

    try:
        from context_graph.repository import ContextGraphRepository

        repo = ContextGraphRepository()
        repo.record_observation(
            observation_type="target_hit",
            ticker=str(ticker),
            payload={
                "timestamp": datetime.now(IST).isoformat(),
                "type": "target_hit",
                "ticker": ticker,
                "entry_price": entry_price,
                "target_price": target_price,
                "pnl_pct": pnl_pct,
                "lesson": f"{ticker} hit target at Rs {target_price} (+{pnl_pct:.1f}%)",
            },
            source="event_handler:target_hit",
        )
        repo.close()
    except Exception as e:
        print(f"handle_target_hit: observation failed: {e}")


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
            "Please re-authenticate to avoid disruption.",
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
            "Position sizing and stops adjusted automatically.",
        )
    except Exception as e:
        print(f"handle_regime_change: Telegram failed: {e}")


async def handle_bounded_exception(event: BusEvent) -> None:
    """Run Phase 14 advisory analysis only when the deterministic classifier opts in."""
    if not cfg.learning.exception_reasoning.enabled:
        return
    from cognition.intraday import ExceptionAnalyst

    analyst = ExceptionAnalyst()
    case = analyst.classify_event(event)
    if case is None:
        return
    advice = await analyst.analyze(case)
    print(
        f"[EVENT] Exception advice: {case.kind} {case.ticker or 'MARKET'} "
        f"-> {advice.advisory_action} (advisory_only={advice.advisory_only})"
    )


# ─────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────


def register_all_handlers(bus=None) -> None:
    """Register all event handlers with the event bus."""
    target_bus = bus or event_bus
    target_bus.subscribe(EventType.GTT_ALERT, handle_gtt_triggered)
    target_bus.subscribe(EventType.NEWS_BREAK, handle_position_news)
    target_bus.subscribe(EventType.MARKET_NEWS_DIGEST, handle_market_news_digest)
    target_bus.subscribe(EventType.STOP_HIT, handle_stop_hit)
    target_bus.subscribe(EventType.TARGET_HIT, handle_target_hit)
    target_bus.subscribe(EventType.AUTH_EXPIRING, handle_auth_expiring)
    target_bus.subscribe(EventType.REGIME_CHANGE, handle_regime_change)
    for event_type in (
        EventType.ERROR,
        EventType.NEWS_BREAK,
        EventType.REGIME_CHANGE,
        EventType.VIX_SPIKE,
    ):
        target_bus.subscribe(event_type, handle_bounded_exception)
    print("EventHandlers: registered 11 handlers")
