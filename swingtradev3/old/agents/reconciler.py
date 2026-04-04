from __future__ import annotations

from swingtradev3.auth.kite.client import fetch_gtts, fetch_holdings, has_kite_session
from swingtradev3.config import cfg
from swingtradev3.logging_config import get_logger
from swingtradev3.models import AccountState
from swingtradev3.tools.execution.alerts import AlertsTool
from swingtradev3.tools.execution.gtt_manager import GTTManager


class Reconciler:
    """Startup reconciliation: state.json vs live Kite.

    Design doc section 4.3 — four scenarios:
    1. Orphaned position (Kite has, state doesn't) → alert, never auto-close
    2. Stale state (state has, Kite doesn't) → remove from state, log
    3. Missing GTT (position exists, stop GTT missing) → alert + emergency GTT
    4. Full agreement → log OK
    """

    def __init__(
        self,
        alerts: AlertsTool | None = None,
        gtt_manager: GTTManager | None = None,
    ) -> None:
        self.alerts = alerts or AlertsTool()
        self.gtt_manager = gtt_manager or GTTManager()
        self.log = get_logger("decisions")

    async def reconcile(self, state: AccountState) -> AccountState:
        if cfg.trading.mode.value == "live":
            return await self._reconcile_live(state)
        return await self._reconcile_paper(state)

    # -- Paper / backtest mode ------------------------------------------------

    async def _reconcile_paper(self, state: AccountState) -> AccountState:
        """Validate GTT simulator consistency for paper positions."""
        issues = False
        for position in state.positions:
            key = position.stop_gtt_id or position.entry_order_id or position.ticker
            gtt = await self.gtt_manager.get_gtt_async(key)
            if gtt is None:
                issues = True
                await self.alerts.send_alert(
                    f"{position.ticker}: stop-loss GTT missing in paper simulator",
                    level="warning",
                )
                self.log.warning("Missing paper GTT for {}", position.ticker)
        if not issues:
            self.log.info("Reconciliation: OK (paper mode)")
        return state

    # -- Live mode ------------------------------------------------------------

    async def _reconcile_live(self, state: AccountState) -> AccountState:
        """Compare Kite holdings + GTTs vs state.json."""
        if not has_kite_session():
            self.log.warning("No Kite session — skipping live reconciliation")
            await self.alerts.send_alert(
                "Reconciliation skipped: no Kite session available",
                level="warning",
            )
            return state

        try:
            live_holdings = fetch_holdings()
            live_gtts = fetch_gtts()
        except Exception as exc:
            self.log.error("Reconciliation failed — Kite API error: {}", exc)
            await self.alerts.send_alert(
                f"Reconciliation failed: could not reach Kite — {exc}",
                level="critical",
            )
            return state

        live_tickers = self._build_holdings_map(live_holdings)
        state_tickers = {p.ticker: p for p in state.positions}
        active_gtt_ids = self._build_active_gtt_set(live_gtts)
        issues_found = False

        # 1. Orphaned: Kite has position, state.json does not
        for ticker, holding in live_tickers.items():
            if ticker not in state_tickers:
                issues_found = True
                await self.alerts.send_alert(
                    f"ORPHANED POSITION: {ticker} qty={holding['quantity']} "
                    f"avg={holding['average_price']:.2f} in Kite but not in state.json. "
                    f"Manual review required — will NOT auto-close.",
                    level="critical",
                )
                self.log.warning("Orphaned position: {}", ticker)

        # 2. Stale: state.json has position, Kite does not
        stale: list[str] = []
        for ticker in state_tickers:
            if ticker not in live_tickers:
                issues_found = True
                stale.append(ticker)
                self.log.warning("Stale position: {} — removing from state", ticker)
        if stale:
            state.positions = [p for p in state.positions if p.ticker not in stale]

        # 3. Missing GTT: position exists but stop-loss GTT gone
        for position in state.positions:
            gtt_missing = False
            if not position.stop_gtt_id:
                gtt_missing = True
            elif position.stop_gtt_id not in active_gtt_ids:
                gtt_missing = True

            if gtt_missing:
                issues_found = True
                await self.alerts.send_alert(
                    f"{position.ticker}: stop-loss GTT missing. "
                    f"Placing emergency GTT at stop={position.stop_price}.",
                    level="critical",
                )
                await self._place_emergency_gtt(position)

        # 4. Full agreement
        if not issues_found:
            self.log.info("Reconciliation: OK")

        return state

    async def _place_emergency_gtt(self, position) -> None:
        """Place an emergency stop-loss GTT for an unprotected position."""
        try:
            gtt = await self.gtt_manager.place_gtt_async(
                position.entry_order_id or position.ticker,
                position.ticker,
                position.stop_price,
                position.target_price,
                quantity=position.quantity,
            )
            position.stop_gtt_id = gtt.position_id
            self.log.info("Emergency GTT placed for {}: {}", position.ticker, gtt.position_id)
        except Exception as exc:
            self.log.error("Failed to place emergency GTT for {}: {}", position.ticker, exc)
            await self.alerts.send_alert(
                f"CRITICAL: Could not place emergency GTT for {position.ticker}: {exc}. "
                f"Position is UNPROTECTED.",
                level="critical",
            )

    @staticmethod
    def _build_holdings_map(holdings: list[dict]) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for h in holdings:
            ticker = str(h.get("tradingsymbol", ""))
            qty = int(h.get("quantity", 0))
            if qty > 0 and ticker:
                result[ticker] = {
                    "quantity": qty,
                    "average_price": float(h.get("average_price", 0.0)),
                }
        return result

    @staticmethod
    def _build_active_gtt_set(gtts: list[dict]) -> set[str]:
        active: set[str] = set()
        for g in gtts:
            gtt_id = str(g.get("id", ""))
            status = str(g.get("status", "")).lower()
            if gtt_id and status not in (
                "cancelled",
                "deleted",
                "disabled",
                "expired",
                "rejected",
            ):
                active.add(gtt_id)
        return active
