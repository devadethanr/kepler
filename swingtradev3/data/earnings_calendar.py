from __future__ import annotations

from datetime import date
from pathlib import Path

from paths import CONTEXT_DIR
from storage import read_json, write_json


class EarningsCalendar:
    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "earnings_calendar.json")

    def load(self) -> dict[str, date]:
        payload = read_json(self.cache_path, {})
        return {ticker: date.fromisoformat(value) for ticker, value in payload.items()}

    def store(self, payload: dict[str, date]) -> None:
        write_json(self.cache_path, {k: v.isoformat() for k, v in payload.items()})
