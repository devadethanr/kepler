from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
import os
from typing import Any
from urllib.parse import parse_qs, urlparse

from kiteconnect import KiteConnect

from swingtradev3.auth.kite.session_store import KiteSessionPayload, load_kite_session, save_kite_session


def build_kite_client(access_token: str | None = None) -> KiteConnect:
    api_key = os.getenv("KITE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("KITE_API_KEY is missing")
    client = KiteConnect(api_key=api_key)
    token = (access_token or os.getenv("KITE_ACCESS_TOKEN", "")).strip()
    if not token:
        stored = load_kite_session()
        if stored is not None:
            token = stored.access_token
    if token:
        client.set_access_token(token)
    return client


def has_kite_session() -> bool:
    return load_kite_session() is not None or bool(os.getenv("KITE_ACCESS_TOKEN", "").strip())


def extract_request_token(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("request_token input is empty")
    if "request_token=" not in candidate:
        return candidate
    parsed = urlparse(candidate)
    token = parse_qs(parsed.query).get("request_token", [""])[0].strip()
    if not token:
        raise ValueError("Could not find request_token in the supplied URL")
    return token


def exchange_request_token(request_token: str) -> KiteSessionPayload:
    api_key = os.getenv("KITE_API_KEY", "").strip()
    api_secret = os.getenv("KITE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise RuntimeError("KITE_API_KEY and KITE_API_SECRET are required")

    client = KiteConnect(api_key=api_key)
    session_data = client.generate_session(request_token, api_secret=api_secret)
    access_token = str(session_data["access_token"])
    client.set_access_token(access_token)
    profile = client.profile()

    payload = KiteSessionPayload(
        api_key=api_key,
        access_token=access_token,
        public_token=session_data.get("public_token"),
        user_id=profile.get("user_id") or session_data.get("user_id"),
        user_name=profile.get("user_name"),
        user_shortname=profile.get("user_shortname"),
        email=profile.get("email"),
        broker=profile.get("broker"),
        user_type=profile.get("user_type"),
        login_time=profile.get("login_time"),
        raw_session=dict(session_data),
    )
    save_kite_session(payload)
    os.environ["KITE_ACCESS_TOKEN"] = access_token
    return payload


def fetch_profile() -> dict[str, Any]:
    client = build_kite_client()
    return client.profile()


def fetch_positions() -> dict[str, Any]:
    client = build_kite_client()
    return client.positions()


def fetch_holdings() -> list[dict[str, Any]]:
    client = build_kite_client()
    return client.holdings()


def fetch_gtts() -> list[dict[str, Any]]:
    client = build_kite_client()
    return client.get_gtts()


def fetch_ltp(exchange: str, ticker: str) -> float:
    client = build_kite_client()
    key = f"{exchange}:{ticker}"
    payload = client.ltp(key)
    data = payload.get(key) or {}
    return float(data.get("last_price", 0.0))


@lru_cache(maxsize=8)
def _instrument_token_map(api_key: str, access_token: str, exchange: str) -> dict[str, int]:
    client = KiteConnect(api_key=api_key)
    client.set_access_token(access_token)
    rows = client.instruments(exchange)
    return {
        str(row["tradingsymbol"]): int(row["instrument_token"])
        for row in rows
        if row.get("tradingsymbol") and row.get("instrument_token") is not None
    }


def resolve_instrument_token(ticker: str, exchange: str) -> int:
    session = load_kite_session()
    api_key = os.getenv("KITE_API_KEY", "").strip()
    access_token = os.getenv("KITE_ACCESS_TOKEN", "").strip()
    if session is not None:
        api_key = session.api_key
        access_token = session.access_token
    if not api_key or not access_token:
        raise RuntimeError("Kite session is unavailable")
    lookup = _instrument_token_map(api_key, access_token, exchange)
    if ticker not in lookup:
        raise KeyError(f"Instrument token not found for {exchange}:{ticker}")
    return lookup[ticker]


def fetch_historical_data(
    ticker: str,
    exchange: str,
    interval: str,
    lookback_days: int = 400,
) -> list[dict[str, Any]]:
    client = build_kite_client()
    instrument_token = resolve_instrument_token(ticker, exchange)
    to_date = datetime.now()
    from_date = to_date - timedelta(days=lookback_days)
    return client.historical_data(instrument_token, from_date, to_date, interval)


def place_live_order(
    *,
    exchange: str,
    ticker: str,
    side: str,
    quantity: int,
    price: float,
    order_type: str = "LIMIT",
    product: str = "CNC",
    variety: str = "regular",
) -> str:
    client = build_kite_client()
    return str(
        client.place_order(
            variety=variety,
            exchange=exchange,
            tradingsymbol=ticker,
            transaction_type=side.upper(),
            quantity=quantity,
            product=product,
            order_type=order_type,
            price=price,
        )
    )


def place_live_gtt(
    *,
    exchange: str,
    ticker: str,
    quantity: int,
    stop_price: float,
    target_price: float,
    last_price: float,
) -> str:
    client = build_kite_client()
    orders = [
        {
            "exchange": exchange,
            "tradingsymbol": ticker,
            "transaction_type": "SELL",
            "quantity": quantity,
            "order_type": "LIMIT",
            "product": "CNC",
            "price": stop_price,
        },
        {
            "exchange": exchange,
            "tradingsymbol": ticker,
            "transaction_type": "SELL",
            "quantity": quantity,
            "order_type": "LIMIT",
            "product": "CNC",
            "price": target_price,
        },
    ]
    return str(
        client.place_gtt(
            trigger_type=client.GTT_TYPE_OCO,
            tradingsymbol=ticker,
            exchange=exchange,
            trigger_values=[stop_price, target_price],
            last_price=last_price,
            orders=orders,
        )
    )


def modify_live_gtt(
    *,
    trigger_id: str,
    exchange: str,
    ticker: str,
    quantity: int,
    stop_price: float,
    target_price: float,
    last_price: float,
) -> None:
    client = build_kite_client()
    orders = [
        {
            "exchange": exchange,
            "tradingsymbol": ticker,
            "transaction_type": "SELL",
            "quantity": quantity,
            "order_type": "LIMIT",
            "product": "CNC",
            "price": stop_price,
        },
        {
            "exchange": exchange,
            "tradingsymbol": ticker,
            "transaction_type": "SELL",
            "quantity": quantity,
            "order_type": "LIMIT",
            "product": "CNC",
            "price": target_price,
        },
    ]
    client.modify_gtt(
        trigger_id=trigger_id,
        trigger_type=client.GTT_TYPE_OCO,
        tradingsymbol=ticker,
        exchange=exchange,
        trigger_values=[stop_price, target_price],
        last_price=last_price,
        orders=orders,
    )


def delete_live_gtt(trigger_id: str) -> None:
    client = build_kite_client()
    client.delete_gtt(trigger_id)
