from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from models import CorporateAction
from paths import CONTEXT_DIR
from storage import read_json, write_json


class CorporateActionsStore:
    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "corporate_actions.json")

    def load(self) -> list[CorporateAction]:
        payload = read_json(self.cache_path, [])
        return [CorporateAction.model_validate(item) for item in payload]

    def store(self, actions: list[CorporateAction]) -> None:
        write_json(self.cache_path, [action.model_dump(mode="json") for action in actions])

    def upcoming(self, ticker: str, days: int) -> list[CorporateAction]:
        cutoff = date.today() + timedelta(days=days)
        return [
            action
            for action in self.load()
            if action.ticker == ticker and date.today() <= action.ex_date <= cutoff
        ]
