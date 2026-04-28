from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from broker.kite_stream import KiteBrokerStream

if TYPE_CHECKING:
    from .quote_cache import QuoteCache


_broker_stream: KiteBrokerStream | None = None
_mutation_lock: asyncio.Lock | None = None
_quote_cache: "QuoteCache | None" = None


def bind_broker_stream(stream: KiteBrokerStream | None) -> None:
    global _broker_stream
    _broker_stream = stream


def get_broker_stream() -> KiteBrokerStream | None:
    return _broker_stream


def bind_mutation_lock(lock: asyncio.Lock | None) -> None:
    global _mutation_lock
    _mutation_lock = lock


def get_mutation_lock() -> asyncio.Lock | None:
    return _mutation_lock


def bind_quote_cache(cache: "QuoteCache | None") -> None:
    global _quote_cache
    _quote_cache = cache


def get_quote_cache() -> "QuoteCache | None":
    return _quote_cache
