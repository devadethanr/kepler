from __future__ import annotations

from pathlib import Path
from typing import Any

from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json


class Nifty200Loader:
    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "nifty200.json")

    def load_entries(self) -> list[dict[str, str]]:
        payload = read_json(self.cache_path, [])
        entries: list[dict[str, str]] = []
        for item in payload:
            if isinstance(item, str):
                entries.append({"ticker": item, "name": item})
            elif isinstance(item, dict):
                ticker = str(item.get("ticker") or item.get("symbol") or "").strip()
                if not ticker:
                    continue
                name = str(item.get("name") or item.get("company_name") or ticker).strip() or ticker
                entries.append({"ticker": ticker, "name": name})
        return entries

    def load(self) -> list[str]:
        return [item["ticker"] for item in self.load_entries()]

    def name_for(self, ticker: str) -> str:
        for item in self.load_entries():
            if item["ticker"] == ticker:
                return item["name"]
        return ticker

    def store(self, tickers: list[str] | list[dict[str, Any]]) -> None:
        write_json(self.cache_path, tickers)
