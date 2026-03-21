from __future__ import annotations

from datetime import datetime, timedelta

from swingtradev3.models import PendingApproval
from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json


class TelegramHandler:
    def __init__(self) -> None:
        self.path = CONTEXT_DIR / "pending_approvals.json"

    def _load(self) -> list[PendingApproval]:
        return [PendingApproval.model_validate(item) for item in read_json(self.path, [])]

    def _save(self, approvals: list[PendingApproval]) -> None:
        write_json(self.path, [item.model_dump(mode="json") for item in approvals])

    def record_approval(self, ticker: str, approved: bool) -> None:
        approvals = self._load()
        for item in approvals:
            if item.ticker == ticker:
                item.approved = approved
        self._save(approvals)

    def expire_stale(self, now: datetime | None = None) -> list[str]:
        now = now or datetime.utcnow()
        approvals = self._load()
        expired = [item.ticker for item in approvals if item.expires_at <= now]
        approvals = [item for item in approvals if item.expires_at > now]
        self._save(approvals)
        return expired

    @staticmethod
    def build_expiry(created_at: datetime, timeout_hours: int) -> datetime:
        return created_at + timedelta(hours=timeout_hours)
