from __future__ import annotations

from pathlib import Path

from data.nifty200_loader import Nifty200Loader
from paths import CONTEXT_DIR


class Nifty50Loader(Nifty200Loader):
    def __init__(self, cache_path: Path | None = None) -> None:
        super().__init__(cache_path=cache_path or (CONTEXT_DIR / "nifty50.json"))
