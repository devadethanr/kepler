from __future__ import annotations

import os

from auth.kite.session_store import load_kite_session
from broker.kite_rest import has_kite_session
from logging_config import get_logger


class TokenManager:
    def __init__(self) -> None:
        self.log = get_logger("decisions")

    async def refresh(self) -> None:
        stored = load_kite_session()
        if stored is not None and stored.access_token:
            os.environ["KITE_API_KEY"] = stored.api_key
            os.environ["KITE_ACCESS_TOKEN"] = stored.access_token
            self.log.info("Loaded Kite credentials from persisted session")
            return
        if os.getenv("KITE_API_KEY") and os.getenv("KITE_ACCESS_TOKEN"):
            self.log.info("Kite credentials already present in environment")
            return
        if not has_kite_session():
            self.log.warning("Kite access token missing; live mode will remain unavailable")
            return
        self.log.warning("Kite access token missing; live mode will remain unavailable")
