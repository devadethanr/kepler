from __future__ import annotations

from swingtradev3.logging_config import get_logger
from swingtradev3.models import AccountState
from swingtradev3.tools.alerts import AlertsTool
from swingtradev3.tools.gtt_manager import GTTManager


class Reconciler:
    def __init__(
        self,
        alerts: AlertsTool | None = None,
        gtt_manager: GTTManager | None = None,
    ) -> None:
        self.alerts = alerts or AlertsTool()
        self.gtt_manager = gtt_manager or GTTManager()
        self.log = get_logger("decisions")

    async def reconcile(self, state: AccountState) -> AccountState:
        for position in state.positions:
            gtt = await self.gtt_manager.get_gtt_async(position.stop_gtt_id or position.entry_order_id or position.ticker)
            if gtt is None and position.stop_gtt_id:
                await self.alerts.send_alert(
                    f"{position.ticker}: stop-loss GTT missing, manual review required",
                    level="warning",
                )
                self.log.warning("Missing GTT detected for {}", position.ticker)
        return state
