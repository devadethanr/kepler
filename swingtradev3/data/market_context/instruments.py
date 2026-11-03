"""Identify candidates in an already downloaded Kite instrument master.

An index master row is not a futures contract, quote, entitlement, or data licence.
This parser performs no network requests and does not choose a futures roll.
"""

from collections.abc import Iterable, Mapping


def kite_master_candidates(rows: Iterable[Mapping[str, str]]) -> list[dict[str, str | None]]:
    candidates = []
    for row in rows:
        exchange = (row.get("exchange") or "").strip().upper()
        symbol = (row.get("tradingsymbol") or "").strip().upper()
        name = (row.get("name") or "").strip().upper()
        segment = (row.get("segment") or "").strip().upper()
        kind = (row.get("instrument_type") or "").strip().upper()
        if exchange == "NSEIX" and segment == "INDICES" and symbol == "GIFT NIFTY":
            scope = "gift_nifty"
        elif segment == "INDICES" and (
            symbol in {"STI", "STRAITS TIMES INDEX"} or name == "STRAITS TIMES INDEX"
        ):
            scope = "singapore_sti"
        else:
            continue
        candidates.append(
            {
                "scope": scope,
                "exchange": exchange,
                "symbol": symbol,
                "name": name or None,
                "segment": segment,
                "instrument_type": kind or None,
                "expiry": (row.get("expiry") or "").strip() or None,
                "instrument_token": (row.get("instrument_token") or "").strip() or None,
                "qualification": "master_entry_only_quote_entitlement_unverified",
            }
        )
    return candidates
