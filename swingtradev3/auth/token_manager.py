from __future__ import annotations

import os

from auth.kite.session_store import load_kite_session
from logging_config import get_logger


class TokenManager:
    def __init__(self) -> None:
        self.log = get_logger("decisions")

    async def refresh(self) -> None:
        token = os.getenv("KITE_ACCESS_TOKEN")
        if token:
            self.log.info("Kite access token already present")
            return
        stored = load_kite_session()
        if stored is not None and stored.access_token:
            os.environ["KITE_ACCESS_TOKEN"] = stored.access_token
            self.log.info("Loaded Kite access token from persisted session")
            return
        self.log.warning("Kite access token missing; live mode will remain unavailable")
