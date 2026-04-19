from __future__ import annotations

import asyncio
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from broker.kite_rest import fetch_ltp


QuoteSource = str  # "websocket" | "rest" | "startup" | "unknown"


@dataclass(slots=True)
class QuoteSnapshot:
    ticker: str
    last_price: float
    last_trade_time: datetime | None
    received_at: datetime
    source: QuoteSource

    def age_seconds(self, *, now: datetime) -> float:
        return (now - self.received_at).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "last_price": self.last_price,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "received_at": self.received_at.isoformat(),
            "source": self.source,
        }


def _coerce_last_trade_time(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


class QuoteCache:
    """Per-ticker last-price cache with freshness tracking.

    Primary feed is the Kite WebSocket stream (via ``broker_stream.latest_quotes_by_ticker``).
    Each newly observed quote is stamped with a local ``received_at`` so the reconciler
    can detect a stalled stream even while the cached dict still holds old values.
    ``fetch_rest_fallback`` performs a single REST LTP call as a degraded fallback.
    """

    def __init__(
        self,
        broker_stream: Any = None,
        *,
        rest_fetcher: Callable[[str, str], float] | None = None,
        clock: Callable[[], datetime] | None = None,
        exchange: str = "NSE",
    ) -> None:
        self._broker_stream = broker_stream
        self._rest_fetcher = rest_fetcher or fetch_ltp
        self._clock = clock or datetime.now
        self._exchange = exchange
        self._snapshots: dict[str, QuoteSnapshot] = {}
        self._lock = threading.Lock()

    def bind_broker_stream(self, stream: Any) -> None:
        self._broker_stream = stream

    def is_stream_connected(self) -> bool:
        stream = self._broker_stream
        if stream is None:
            return False
        return bool(getattr(stream, "_connected", False))

    def ingest_tick(
        self,
        ticker: str,
        tick_data: dict[str, Any],
        *,
        source: QuoteSource = "websocket",
    ) -> QuoteSnapshot | None:
        normalized = ticker.strip().upper()
        if not normalized:
            return None
        raw_price = tick_data.get("last_price")
        if raw_price in (None, ""):
            return None
        try:
            last_price = float(raw_price)
        except (TypeError, ValueError):
            return None
        if last_price <= 0:
            return None
        snapshot = QuoteSnapshot(
            ticker=normalized,
            last_price=last_price,
            last_trade_time=_coerce_last_trade_time(tick_data.get("last_trade_time")),
            received_at=self._clock(),
            source=source,
        )
        with self._lock:
            existing = self._snapshots.get(normalized)
            if (
                existing is not None
                and existing.last_price == snapshot.last_price
                and existing.last_trade_time == snapshot.last_trade_time
                and existing.source == snapshot.source
            ):
                return existing
            self._snapshots[normalized] = snapshot
        return snapshot

    def refresh_from_stream(self, tickers: Iterable[str] | None = None) -> int:
        stream = self._broker_stream
        if stream is None:
            return 0
        snapshot_fn = getattr(stream, "snapshot_quotes", None)
        if callable(snapshot_fn):
            latest = snapshot_fn()
        else:
            # Fallback for mocks / older stubs that expose the raw dict.
            latest = dict(getattr(stream, "latest_quotes_by_ticker", {}) or {})
        if not latest:
            return 0
        target: set[str] | None = None
        if tickers is not None:
            target = {t.strip().upper() for t in tickers if t}
        updated = 0
        for raw_ticker, tick in latest.items():
            normalized = str(raw_ticker).strip().upper()
            if target is not None and normalized not in target:
                continue
            if not isinstance(tick, dict):
                continue
            existing = self._snapshots.get(normalized)
            new_ltt = _coerce_last_trade_time(tick.get("last_trade_time"))
            raw_price = tick.get("last_price")
            try:
                new_price = float(raw_price) if raw_price not in (None, "") else 0.0
            except (TypeError, ValueError):
                continue
            if new_price <= 0:
                continue
            if (
                existing is not None
                and existing.last_price == new_price
                and existing.last_trade_time == new_ltt
                and existing.source == "websocket"
            ):
                continue
            self.ingest_tick(normalized, tick, source="websocket")
            updated += 1
        return updated

    def get_quote(self, ticker: str) -> QuoteSnapshot | None:
        normalized = ticker.strip().upper()
        if not normalized:
            return None
        self.refresh_from_stream([normalized])
        with self._lock:
            return self._snapshots.get(normalized)

    def staleness_seconds(self, ticker: str) -> float | None:
        snapshot = self.get_quote(ticker)
        if snapshot is None:
            return None
        return snapshot.age_seconds(now=self._clock())

    def check_freshness(
        self,
        tickers: Iterable[str],
        *,
        max_age_seconds: float,
    ) -> dict[str, Any]:
        normalized_tickers = [t.strip().upper() for t in tickers if t]
        self.refresh_from_stream(normalized_tickers)
        now = self._clock()
        fresh: list[str] = []
        stale: list[dict[str, Any]] = []
        missing: list[str] = []
        with self._lock:
            for ticker in normalized_tickers:
                snapshot = self._snapshots.get(ticker)
                if snapshot is None:
                    missing.append(ticker)
                    continue
                age = snapshot.age_seconds(now=now)
                if age > max_age_seconds:
                    stale.append(
                        {
                            "ticker": ticker,
                            "age_seconds": round(age, 2),
                            "source": snapshot.source,
                            "last_price": snapshot.last_price,
                        }
                    )
                else:
                    fresh.append(ticker)
        total = len(normalized_tickers)
        stale_count = len(stale) + len(missing)
        stale_ratio = (stale_count / total) if total > 0 else 0.0
        return {
            "checked_at": now.isoformat(),
            "total": total,
            "fresh": fresh,
            "stale": stale,
            "missing": missing,
            "stale_ratio": round(stale_ratio, 4),
            "stream_connected": self.is_stream_connected(),
        }

    async def fetch_rest_fallback(
        self,
        ticker: str,
        *,
        exchange: str | None = None,
    ) -> QuoteSnapshot | None:
        normalized = ticker.strip().upper()
        if not normalized:
            return None
        use_exchange = exchange or self._exchange
        try:
            price = await asyncio.to_thread(self._rest_fetcher, use_exchange, normalized)
        except Exception:
            return None
        if not price or price <= 0:
            return None
        snapshot = QuoteSnapshot(
            ticker=normalized,
            last_price=float(price),
            last_trade_time=None,
            received_at=self._clock(),
            source="rest",
        )
        with self._lock:
            self._snapshots[normalized] = snapshot
        return snapshot

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {ticker: snap.to_dict() for ticker, snap in self._snapshots.items()}

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
