from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, model_validator

from paths import CONTEXT_DIR
from storage import read_json, write_json


KITE_SESSION_PATH = CONTEXT_DIR / "auth" / "kite_session.json"
IST = ZoneInfo("Asia/Kolkata")


class KiteSessionPayload(BaseModel):
    api_key: str
    access_token: str
    public_token: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    user_shortname: str | None = None
    email: str | None = None
    broker: str | None = None
    user_type: str | None = None
    login_time: str | None = None
    created_at: str | None = Field(default_factory=lambda: datetime.now(IST).isoformat())
    raw_session: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if payload.get("created_at") is None:
            payload["created_at"] = payload.get("login_time") or datetime.now(IST).isoformat()
        return payload

    def reference_time(self) -> datetime | None:
        for value in (self.login_time, self.created_at):
            if not value:
                continue
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=IST)
            return parsed.astimezone(IST)
        return None

    def is_probably_expired(self, now: datetime | None = None) -> bool:
        reference = self.reference_time()
        if reference is None:
            return False
        current = (now or datetime.now(IST)).astimezone(IST)
        expiry_date = reference.date() + timedelta(days=1)
        expiry = datetime.combine(expiry_date, dt_time(6, 0), tzinfo=IST)
        return current >= expiry


def load_kite_session() -> KiteSessionPayload | None:
    payload = read_json(KITE_SESSION_PATH, {})
    if not payload:
        return None
    session = KiteSessionPayload.model_validate(payload)
    if session.is_probably_expired():
        return None
    return session


def save_kite_session(payload: KiteSessionPayload) -> None:
    write_json(KITE_SESSION_PATH, payload.model_dump(mode="json"))
