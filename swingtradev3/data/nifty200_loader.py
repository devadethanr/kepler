from __future__ import annotations

from pathlib import Path

from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json


class Nifty200Loader:
    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "nifty200.json")

    def load(self) -> list[str]:
        payload = read_json(self.cache_path, [])
        return [str(item) for item in payload]

    def store(self, tickers: list[str]) -> None:
        write_json(self.cache_path, tickers)
