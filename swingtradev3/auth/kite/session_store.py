from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from paths import CONTEXT_DIR
from storage import read_json, write_json


KITE_SESSION_PATH = CONTEXT_DIR / "auth" / "kite_session.json"


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
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    raw_session: dict[str, Any] = Field(default_factory=dict)


def load_kite_session() -> KiteSessionPayload | None:
    payload = read_json(KITE_SESSION_PATH, {})
    if not payload:
        return None
    return KiteSessionPayload.model_validate(payload)


def save_kite_session(payload: KiteSessionPayload) -> None:
    write_json(KITE_SESSION_PATH, payload.model_dump(mode="json"))

