from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from broker.kite_stream import build_kite_ticker
from kiteconnect import KiteTicker
from kiteconnect.ticker import log as ticker_log


@dataclass(slots=True)
class WebSocketProbeResult:
    connected: bool
    order_update_handler_ready: bool
    error: str | None = None
    close_code: int | None = None
    close_reason: str | None = None
def probe_order_update_websocket(timeout_seconds: float = 8.0) -> WebSocketProbeResult:
    ticker = build_kite_ticker()
    connected = threading.Event()
    closed = threading.Event()
    previous_log_level = ticker_log.level
    state: dict[str, object] = {
        "connected": False,
        "error": None,
        "close_code": None,
        "close_reason": None,
    }

    def on_connect(ws: KiteTicker, _response: object) -> None:
        state["connected"] = True
        connected.set()
        ws.close(code=1000, reason="phase0-readiness")

    def on_close(_ws: KiteTicker, code: int | None, reason: str | None) -> None:
        state["close_code"] = code
        state["close_reason"] = reason
        closed.set()

    def on_error(ws: KiteTicker, code: int | None, reason: str | None) -> None:
        state["error"] = f"code={code} reason={reason}"
        connected.set()
        try:
            ws.close(code=code, reason=reason)
        except Exception:
            pass

    def on_order_update(_ws: KiteTicker, _data: dict[str, object]) -> None:
        return None

    ticker.on_connect = on_connect
    ticker.on_close = on_close
    ticker.on_error = on_error
    ticker.on_order_update = on_order_update

    ticker_log.setLevel(logging.CRITICAL)
    try:
        try:
            ticker.connect(threaded=True)
        except Exception as exc:
            return WebSocketProbeResult(
                connected=False,
                order_update_handler_ready=True,
                error=str(exc),
            )

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if connected.wait(timeout=0.1):
                break

        if not bool(state["connected"]) and state["error"] is None:
            state["error"] = f"Timed out after {timeout_seconds:.1f}s waiting for WebSocket connect"

        if bool(state["connected"]):
            closed.wait(timeout=2.0)

        try:
            ticker.close(code=1000, reason="phase0-readiness-cleanup")
        except Exception:
            pass
        try:
            ticker.stop()
        except Exception:
            pass
    finally:
        ticker_log.setLevel(previous_log_level)

    return WebSocketProbeResult(
        connected=bool(state["connected"]),
        order_update_handler_ready=ticker.on_order_update is not None,
        error=state["error"] if isinstance(state["error"], str) else None,
        close_code=int(state["close_code"]) if isinstance(state["close_code"], int) else None,
        close_reason=state["close_reason"] if isinstance(state["close_reason"], str) else None,
    )
