from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from kiteconnect import KiteTicker

from .reducer import BrokerReducer
from .kite_rest import resolve_instrument_token, resolve_kite_credentials


def build_kite_ticker(access_token: str | None = None) -> KiteTicker:
    api_key, token = resolve_kite_credentials(access_token=access_token)
    if not token:
        raise RuntimeError("Kite access token is unavailable")

    return KiteTicker(
        api_key=api_key,
        access_token=token,
        reconnect=True,
        reconnect_max_delay=15,
        reconnect_max_tries=300,
    )


class KiteBrokerStream:
    def __init__(
        self,
        reducer: BrokerReducer | None = None,
        *,
        ticker_factory: Callable[[], KiteTicker] = build_kite_ticker,
        logger: logging.Logger | None = None,
    ) -> None:
        self.reducer = reducer or BrokerReducer()
        self.ticker_factory = ticker_factory
        self.logger = logger or logging.getLogger("broker.kite_stream")
        self._ticker: KiteTicker | None = None
        self._lock = threading.Lock()
        self._connected = False
        self._reconnect_exhausted = False
        self._stop_requested = False
        self._access_token: str | None = None
        self._exchange = "NSE"
        self._tracked_tickers: set[str] = set()
        self._token_to_ticker: dict[int, str] = {}
        self.latest_ticks: dict[int, dict[str, Any]] = {}
        self.latest_quotes_by_ticker: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        self._stop_requested = False
        self.ensure_running()

    def ensure_running(self) -> None:
        with self._lock:
            self._stop_requested = False
            current = self._ticker
            desired_access_token: str | None = None
            try:
                _, desired_access_token = resolve_kite_credentials()
            except Exception:
                desired_access_token = None
            token_changed = (
                current is not None
                and desired_access_token not in (None, "")
                and desired_access_token != self._access_token
            )
            if current is not None:
                try:
                    if current.is_connected() and not token_changed:
                        self._connected = True
                        self._apply_subscriptions(current)
                        return
                except Exception:
                    pass
                if not self._reconnect_exhausted and not token_changed:
                    return
                try:
                    current.close(code=1000, reason="stream-rebuild")
                except Exception:
                    pass
                try:
                    current.stop()
                except Exception:
                    pass
            ticker = self.ticker_factory()
            ticker.on_order_update = self._on_order_update
            ticker.on_ticks = self._on_ticks
            ticker.on_connect = self._on_connect
            ticker.on_close = self._on_close
            ticker.on_error = self._on_error
            ticker.on_reconnect = self._on_reconnect
            ticker.on_noreconnect = self._on_noreconnect
            ticker.connect(threaded=True)
            self._ticker = ticker
            self._connected = False
            self._reconnect_exhausted = False
            self._access_token = desired_access_token

    def stop(self) -> None:
        with self._lock:
            ticker = self._ticker
            self._ticker = None
            self._connected = False
            self._reconnect_exhausted = False
            self._access_token = None
        if ticker is None:
            return
        try:
            ticker.close(code=1000, reason="worker-stop")
        except Exception:
            pass
        try:
            ticker.stop()
        except Exception:
            pass

    def _on_connect(self, ws: KiteTicker, _response: object) -> None:
        self._connected = True
        self._reconnect_exhausted = False
        self._apply_subscriptions(ws)
        self.logger.info("Kite WebSocket connected")

    def _on_close(self, _ws: KiteTicker, code: int | None, reason: str | None) -> None:
        self._connected = False
        self.logger.info("Kite WebSocket closed code=%s reason=%s", code, reason)

    def _on_error(self, _ws: KiteTicker, code: int | None, reason: str | None) -> None:
        self.logger.warning("Kite WebSocket error code=%s reason=%s", code, reason)

    def _on_reconnect(self, _ws: KiteTicker, attempts_count: int) -> None:
        self._connected = False
        self.logger.warning("Kite WebSocket reconnect attempt=%s", attempts_count)

    def _on_noreconnect(self, _ws: KiteTicker) -> None:
        self._connected = False
        self._reconnect_exhausted = True
        self.logger.error("Kite WebSocket exhausted reconnect attempts")

    def _on_order_update(self, _ws: KiteTicker, data: dict[str, Any]) -> None:
        try:
            self.reducer.apply_order_update(data, source="websocket")
        except Exception as exc:
            self.logger.exception("Failed to apply broker order update: %s", exc)

    def _on_ticks(self, _ws: KiteTicker, ticks: list[dict[str, Any]]) -> None:
        for tick in ticks:
            token = int(tick.get("instrument_token") or 0)
            if token <= 0:
                continue
            self.latest_ticks[token] = dict(tick)
            ticker = self._token_to_ticker.get(token)
            if ticker:
                self.latest_quotes_by_ticker[ticker] = dict(tick)

    def set_tracked_tickers(self, tickers: list[str] | set[str], *, exchange: str) -> None:
        normalized = {str(item).strip().upper() for item in tickers if str(item).strip()}
        self._exchange = exchange
        self._tracked_tickers = normalized
        self._token_to_ticker = {}
        for ticker in sorted(normalized):
            try:
                token = resolve_instrument_token(ticker, exchange)
            except Exception as exc:
                self.logger.warning("Failed to resolve instrument token for %s: %s", ticker, exc)
                continue
            self._token_to_ticker[token] = ticker
        current = self._ticker
        if current is not None:
            self._apply_subscriptions(current)

    def get_latest_quote(self, ticker: str) -> dict[str, Any] | None:
        return self.latest_quotes_by_ticker.get(ticker.strip().upper())

    def _apply_subscriptions(self, ticker: KiteTicker) -> None:
        if not self._connected:
            return
        tokens = list(self._token_to_ticker.keys())
        if not tokens:
            return
        try:
            ticker.subscribe(tokens)
            ticker.set_mode(ticker.MODE_FULL, tokens)
        except Exception as exc:
            self.logger.warning("Failed to apply quote subscriptions: %s", exc)
