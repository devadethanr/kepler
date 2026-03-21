from __future__ import annotations

import os

from swingtradev3.logging_config import get_logger


class TokenManager:
    def __init__(self) -> None:
        self.log = get_logger("decisions")

    async def refresh(self) -> None:
        token = os.getenv("KITE_ACCESS_TOKEN")
        if token:
            self.log.info("Kite access token already present")
            return
        self.log.warning("Kite access token missing; live mode will remain unavailable")
