from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from swingtradev3.auth.kite.client import fetch_holdings, fetch_ltp, has_kite_session
from swingtradev3.auth.token_manager import TokenManager
from swingtradev3.config import cfg
from swingtradev3.data.corporate_actions import CorporateActionsStore
from swingtradev3.learning.trade_reviewer import TradeReviewer
from swingtradev3.logging_config import get_logger
from swingtradev3.models import AccountState, PositionState, TradeRecord
from swingtradev3.notifications.telegram_handler import TelegramHandler
from swingtradev3.paths import CONTEXT_DIR, PROJECT_ROOT
from swingtradev3.risk.circuit_limit_checker import is_circuit_hit
from swingtradev3.storage import read_json, write_json
from swingtradev3.tools.execution.alerts import AlertsTool
from swingtradev3.tools.execution.gtt_manager import GTTManager
from swingtradev3.tools.execution.order_execution import OrderExecutionTool
from swingtradev3.agents.reconciler import Reconciler
from swingtradev3.data.nifty200_loader import Nifty200Loader


class ExecutionAgent:
    """Approval handler + GTT lifecycle manager.

    Design doc section 4.2:
    - startup() runs once at 09:15
    - poll() runs every 30 min during market hours (09:15-15:30)
    """

    def __init__(
        self,
        order_tool: OrderExecutionTool | None = None,
        gtt_manager: GTTManager | None = None,
        alerts: AlertsTool | None = None,
        telegram_handler: TelegramHandler | None = None,
        corporate_actions: CorporateActionsStore | None = None,
        reconciler: Reconciler | None = None,
        trade_reviewer: TradeReviewer | None = None,
        token_manager: TokenManager | None = None,
    ) -> None:
        self.order_tool = order_tool or OrderExecutionTool()
        self.gtt_manager = gtt_manager or GTTManager()
        self.alerts = alerts or AlertsTool()
        self.telegram_handler = telegram_handler or TelegramHandler()
        self.corporate_actions = corporate_actions or CorporateActionsStore()
        self.reconciler = reconciler or Reconciler(
            alerts=self.alerts, gtt_manager=self.gtt_manager
        )
        self.trade_reviewer = trade_reviewer or TradeReviewer()
        self.token_manager = token_manager or TokenManager()
        self.nifty_loader = Nifty200Loader()
        self.log = get_logger("trades")

    def _company_name(self, ticker: str) -> str:
        return self.nifty_loader.name_for(ticker)

    # -- State helpers --------------------------------------------------------

    def _pause_active(self) -> bool:
        return (PROJECT_ROOT / "PAUSE").exists()

    def _load_state(self) -> AccountState:
        return AccountState.model_validate(read_json(CONTEXT_DIR / "state.json", {}))

    def _save_state(self, state: AccountState) -> None:
        write_json(CONTEXT_DIR / "state.json", state.model_dump(mode="json"))

    def _load_pending(self) -> list[dict]:
        return read_json(CONTEXT_DIR / "pending_approvals.json", [])

    def _save_pending(self, items: list[dict]) -> None:
        write_json(CONTEXT_DIR / "pending_approvals.json", items)

    def _save_daily_snapshot(self, state: AccountState) -> None:
        """Save daily state snapshot for crash recovery (design doc section 3)."""
        snapshot_dir = CONTEXT_DIR / "daily"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        path = snapshot_dir / f"{date.today().isoformat()}.json"
        write_json(path, state.model_dump(mode="json"))

    # -- Entry validation -----------------------------------------------------

    def _entry_still_valid(self, approval: dict, current_price: float) -> bool:
        """Auto-expire if price moves >max_entry_deviation_pct above entry zone top."""
        entry_high = approval["entry_zone"]["high"]
        max_allowed = entry_high * (1 + cfg.execution.max_entry_deviation_pct / 100)
        return current_price <= max_allowed

    async def _resolve_current_price(self, ticker: str, fallback: float) -> float:
        """Fetch actual LTP from Kite. Falls back to provided value."""
        if cfg.trading.mode.value != "live":
            return fallback
        if has_kite_session():
            try:
                return fetch_ltp(cfg.trading.exchange, ticker)
            except Exception:
                pass
        return fallback

    # -- Startup (design doc 4.2: runs once at 09:15) -------------------------

    async def startup(self) -> AccountState:
        """Startup sequence per design doc section 4.2:
        1. Token refresh
        2. Reconciler runs
        3. Load pending approvals
        4. Check PAUSE file
        5. Send 'Execution agent online' Telegram
        """
        self.log.info("Execution agent starting up")

        # 1. Token refresh
        await self.token_manager.refresh()

        # 2. Reconcile state vs live Kite
        state = self._load_state()
        state = await self.reconciler.reconcile(state)
        self._save_state(state)

        # 3. Load pending
        pending = self._load_pending()
        self.log.info("Loaded {} pending approvals", len(pending))

        # 4 & 5. PAUSE check + online alert
        if self._pause_active():
            await self.alerts.send_alert(
                "Execution agent online — PAUSED (PAUSE file detected)",
                level="warning",
            )
        else:
            await self.alerts.send_alert(
                f"Execution agent online. "
                f"{len(state.positions)} open positions, "
                f"{len(pending)} pending approvals, "
                f"cash ₹{state.cash_inr:,.0f}.",
                level="info",
            )

        return state

    # -- Corporate actions ----------------------------------------------------

    async def _handle_corporate_actions(self, state: AccountState) -> None:
        for position in state.positions:
            actions = self.corporate_actions.upcoming(
                position.ticker,
                cfg.execution.corporate_action_handling.alert_days_before_exdate,
            )
            for action in actions:
                if action.action_type == "dividend":
                    adjusted_stop = position.stop_price - (action.value or 0.0)
                    pending = position.pending_corporate_action
                    if not pending.gtt_adjustment_sent:
                        pending.type = "dividend"
                        pending.amount = action.value
                        pending.ex_date = action.ex_date
                        pending.gtt_adjustment_sent = True
                        pending.adjustment_alert_sent_at = datetime.utcnow()
                        await self.alerts.send_alert(
                            f"{position.ticker} ex-div on {action.ex_date}. Stop will adjust from "
                            f"{position.stop_price} to {adjusted_stop} unless cancelled.",
                            level="warning",
                        )
                    elif pending.adjustment_alert_sent_at:
                        elapsed = datetime.utcnow() - pending.adjustment_alert_sent_at
                        if (
                            elapsed.total_seconds()
                            >= cfg.execution.corporate_action_handling.auto_adjust_timeout_hours
                            * 3600
                        ):
                            position.stop_price = adjusted_stop
                            await self.gtt_manager.modify_gtt_async(
                                position.stop_gtt_id
                                or position.entry_order_id
                                or position.ticker,
                                adjusted_stop,
                                ticker=position.ticker,
                                target_price=position.target_price,
                                quantity=position.quantity,
                            )
                elif action.action_type in {"bonus", "split"}:
                    position.pending_corporate_action.type = action.action_type
                    position.pending_corporate_action.requires_manual_action = True
                    await self.alerts.send_alert(
                        f"{position.ticker} has upcoming {action.action_type}; manual GTT review required.",
                        level="warning",
                    )
                else:
                    await self.alerts.send_alert(
                        f"{position.ticker} has a rights issue event for awareness.",
                        level="info",
                    )

    # -- Trailing stops -------------------------------------------------------

    async def _check_trailing(self, state: AccountState) -> None:
        if not cfg.execution.enable_trailing:
            return
        for position in state.positions:
            if not position.current_price:
                continue
            pnl_pct = ((position.current_price / position.entry_price) - 1) * 100
            position_key = (
                position.stop_gtt_id or position.entry_order_id or position.ticker
            )
            if pnl_pct >= cfg.execution.trail_to_pct:
                new_stop = round(
                    position.entry_price
                    * (1 + cfg.execution.trail_stop_to_locked_profit_pct / 100),
                    2,
                )
                if new_stop > position.stop_price:
                    position.stop_price = new_stop
                    await self.gtt_manager.modify_gtt_async(
                        position_key,
                        new_stop,
                        ticker=position.ticker,
                        target_price=position.target_price,
                        quantity=position.quantity,
                    )
                    self.log.info(
                        "{}: trailing stop to {} (+{}%)",
                        position.ticker,
                        new_stop,
                        cfg.execution.trail_stop_to_locked_profit_pct,
                    )
            elif pnl_pct >= cfg.execution.trail_stop_at_pct:
                new_stop = round(position.entry_price, 2)
                if new_stop > position.stop_price:
                    position.stop_price = new_stop
                    await self.gtt_manager.modify_gtt_async(
                        position_key,
                        new_stop,
                        ticker=position.ticker,
                        target_price=position.target_price,
                        quantity=position.quantity,
                    )
                    self.log.info(
                        "{}: stop moved to breakeven {}", position.ticker, new_stop
                    )

    # -- GTT trigger processing -----------------------------------------------

    async def _process_gtt_triggers(self, state: AccountState) -> None:
        remaining: list[PositionState] = []
        trades = read_json(CONTEXT_DIR / "trades.json", [])
        for position in state.positions:
            key = position.stop_gtt_id or position.entry_order_id or position.ticker
            gtt = await self.gtt_manager.get_gtt_async(key)
            if gtt and gtt.status in {"triggered_stop", "triggered_target"}:
                exit_price = (
                    gtt.stop_price
                    if gtt.status == "triggered_stop"
                    else gtt.target_price
                )
                pnl_abs = (exit_price - position.entry_price) * position.quantity
                pnl_pct = ((exit_price / position.entry_price) - 1) * 100
                trade = TradeRecord(
                    trade_id=f"TRD-{uuid4().hex[:8]}",
                    ticker=position.ticker,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    opened_at=position.opened_at,
                    closed_at=datetime.utcnow(),
                    exit_reason="stop_loss"
                    if gtt.status == "triggered_stop"
                    else "target",
                    pnl_abs=pnl_abs,
                    pnl_pct=pnl_pct,
                    setup_type="unknown",
                    thesis_reasoning=None,
                    research_date=position.research_date,
                    skill_version=position.skill_version,
                )
                trades.append(trade.model_dump(mode="json"))
                self.trade_reviewer.review(trade)
                state.cash_inr += exit_price * position.quantity
                state.realized_pnl += pnl_abs
                await self.alerts.send_profit_alert(
                    ticker=position.ticker,
                    company_name=self._company_name(position.ticker),
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    pnl_amount=pnl_abs,
                    pnl_percent=pnl_pct,
                    exit_reason=trade.exit_reason,
                )
                self.log.info(
                    "{} closed: {} pnl={:.2f}%",
                    position.ticker,
                    trade.exit_reason,
                    pnl_pct,
                )
            else:
                remaining.append(position)
        state.positions = remaining
        write_json(CONTEXT_DIR / "trades.json", trades)

    # -- GTT health check (30-min poll, NOT startup) --------------------------

    async def _check_gtt_health(self, state: AccountState) -> None:
        """Design doc 4.2: if GTT disappears without position close, alert.
        Do NOT re-place automatically during polling — require acknowledgement.
        (Reconciler at startup is more aggressive and places emergency GTTs.)
        """
        for position in state.positions:
            key = position.stop_gtt_id or position.entry_order_id or position.ticker
            gtt = await self.gtt_manager.get_gtt_async(key)
            if gtt is None and position.stop_gtt_id:
                await self.alerts.send_alert(
                    f"GTT MISSING: {position.ticker} stop-loss GTT {position.stop_gtt_id} "
                    f"has disappeared. Position is UNPROTECTED. "
                    f"Original stop: {position.stop_price}. Acknowledge and review.",
                    level="critical",
                )
                self.log.warning(
                    "GTT {} missing for {}", position.stop_gtt_id, position.ticker
                )
            elif gtt and gtt.status == "cancelled":
                await self.alerts.send_alert(
                    f"GTT CANCELLED: {position.ticker} stop-loss GTT was cancelled. "
                    f"Position is UNPROTECTED. Manual intervention required.",
                    level="critical",
                )
                self.log.warning("GTT cancelled for {}", position.ticker)

    # -- Circuit limit check --------------------------------------------------

    async def _check_circuit_limits(self, state: AccountState) -> None:
        """Design doc 4.2: check if held stocks hit NSE circuit limits.
        GTT SL-M orders cannot fill at circuit — alert for manual action.
        """
        for position in state.positions:
            if not position.current_price:
                continue
            # Circuit limits are typically ±5%, ±10%, ±20% of previous close
            # For now we check if the price is at an extreme that warrants alerting
            # In live mode we would fetch circuit limits from Kite instruments
            entry = position.entry_price
            lower_circuit = entry * 0.80  # conservative lower bound
            upper_circuit = entry * 1.20  # conservative upper bound
            if is_circuit_hit(position.current_price, upper_circuit, lower_circuit):
                await self.alerts.send_alert(
                    f"CIRCUIT ALERT: {position.ticker} at {position.current_price} "
                    f"may be near circuit limits. GTT SL-M may not fill. "
                    f"Manual intervention may be required.",
                    level="critical",
                )
                self.log.warning(
                    "Circuit limit alert for {} at {}",
                    position.ticker,
                    position.current_price,
                )

    # -- Update positions with live prices ------------------------------------

    async def _refresh_position_prices(self, state: AccountState) -> None:
        """Fetch current prices for all held positions."""
        for position in state.positions:
            price = await self._resolve_current_price(
                position.ticker, position.current_price or position.entry_price
            )
            position.current_price = price

        # Update unrealized P&L
        state.unrealized_pnl = sum(
            ((p.current_price or p.entry_price) - p.entry_price) * p.quantity
            for p in state.positions
        )

    # -- Main poll loop -------------------------------------------------------

    async def poll(self) -> AccountState:
        """30-min poll during market hours (09:15-15:30)."""
        if self._pause_active():
            await self.alerts.send_alert(
                "Execution paused via PAUSE file", level="warning"
            )
            return self._load_state()

        state = self._load_state()

        # Expire stale approvals
        expired = self.telegram_handler.expire_stale()
        for ticker in expired:
            await self.alerts.send_alert(
                f"{ticker} setup expired — not entered.", level="info"
            )

        # Process approved entries
        pending = self._load_pending()
        remaining: list[dict] = []
        for approval in pending:
            if approval.get("approved") is not True:
                remaining.append(approval)
                continue

            # Fetch actual LTP for entry validation (not entry_zone high)
            current_price = await self._resolve_current_price(
                approval["ticker"], approval["entry_zone"]["high"]
            )
            if not self._entry_still_valid(approval, current_price):
                await self.alerts.send_alert(
                    f"{approval['ticker']} approval expired — price {current_price} "
                    f"moved above valid entry zone ({approval['entry_zone']['high']} "
                    f"+ {cfg.execution.max_entry_deviation_pct}%).",
                    level="warning",
                )
                continue

            result = await self.order_tool.place_order_async(
                state=state,
                ticker=approval["ticker"],
                side="buy",
                score=approval["score"],
                price=current_price,
                stop_price=approval["stop_price"],
                target_price=approval["target_price"],
            )
            if result["status"] != "filled":
                await self.alerts.send_alert(
                    f"{approval['ticker']} was not entered: {result.get('reason', 'unknown')}",
                    level="warning",
                )
                continue

            position = PositionState(
                ticker=approval["ticker"],
                quantity=result["quantity"],
                entry_price=result["average_price"],
                current_price=result["average_price"],
                stop_price=approval["stop_price"],
                target_price=approval["target_price"],
                opened_at=datetime.utcnow(),
                entry_order_id=result["position_id"],
                stop_gtt_id=result["stop_gtt_id"],
                target_gtt_id=result["target_gtt_id"],
                thesis_score=approval["score"],
                research_date=approval.get("research_date"),
                skill_version=approval.get("skill_version"),
                sector=approval.get("sector"),
            )
            state.positions.append(position)
            state.cash_inr -= position.entry_price * position.quantity
            await self.alerts.send_entry_alert(
                ticker=position.ticker,
                company_name=self._company_name(position.ticker),
                quantity=position.quantity,
                entry_price=position.entry_price,
                stop_loss=position.stop_price,
                target=position.target_price,
            )
        self._save_pending(remaining)

        # Refresh position prices from live data
        await self._refresh_position_prices(state)

        # Corporate action handling
        await self._handle_corporate_actions(state)

        # Trailing stops
        await self._check_trailing(state)

        # GTT trigger processing (fills)
        await self._process_gtt_triggers(state)

        # GTT health check (alert for disappeared GTTs — no auto-replace)
        await self._check_gtt_health(state)

        # Circuit limit check
        await self._check_circuit_limits(state)

        # Save state + daily snapshot
        self._save_state(state)
        self._save_daily_snapshot(state)

        self.log.info(
            "Execution poll completed: {} positions, cash ₹{:,.0f}, unrealized ₹{:+,.0f}",
            len(state.positions),
            state.cash_inr,
            state.unrealized_pnl,
        )
        return state
