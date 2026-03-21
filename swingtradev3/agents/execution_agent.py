from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from swingtradev3.config import cfg
from swingtradev3.data.corporate_actions import CorporateActionsStore
from swingtradev3.learning.trade_reviewer import TradeReviewer
from swingtradev3.logging_config import get_logger
from swingtradev3.models import AccountState, PositionState, TradeRecord
from swingtradev3.notifications.telegram_handler import TelegramHandler
from swingtradev3.paths import CONTEXT_DIR, PROJECT_ROOT
from swingtradev3.storage import read_json, write_json
from swingtradev3.tools.alerts import AlertsTool
from swingtradev3.tools.gtt_manager import GTTManager
from swingtradev3.tools.order_execution import OrderExecutionTool
from swingtradev3.agents.reconciler import Reconciler


class ExecutionAgent:
    def __init__(
        self,
        order_tool: OrderExecutionTool | None = None,
        gtt_manager: GTTManager | None = None,
        alerts: AlertsTool | None = None,
        telegram_handler: TelegramHandler | None = None,
        corporate_actions: CorporateActionsStore | None = None,
        reconciler: Reconciler | None = None,
        trade_reviewer: TradeReviewer | None = None,
    ) -> None:
        self.order_tool = order_tool or OrderExecutionTool()
        self.gtt_manager = gtt_manager or GTTManager()
        self.alerts = alerts or AlertsTool()
        self.telegram_handler = telegram_handler or TelegramHandler()
        self.corporate_actions = corporate_actions or CorporateActionsStore()
        self.reconciler = reconciler or Reconciler(alerts=self.alerts, gtt_manager=self.gtt_manager)
        self.trade_reviewer = trade_reviewer or TradeReviewer()
        self.log = get_logger("trades")

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

    def _entry_still_valid(self, approval: dict, current_price: float) -> bool:
        entry_high = approval["entry_zone"]["high"]
        max_allowed = entry_high * (1 + cfg.execution.max_entry_deviation_pct / 100)
        return current_price <= max_allowed

    async def _handle_corporate_actions(self, state: AccountState) -> None:
        for position in state.positions:
            actions = self.corporate_actions.upcoming(
                position.ticker, cfg.execution.corporate_action_handling.alert_days_before_exdate
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
                        if elapsed.total_seconds() >= cfg.execution.corporate_action_handling.auto_adjust_timeout_hours * 3600:
                            position.stop_price = adjusted_stop
                            self.gtt_manager.modify_gtt(position.entry_order_id or position.ticker, adjusted_stop)
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

    async def _check_trailing(self, state: AccountState) -> None:
        for position in state.positions:
            if not position.current_price:
                continue
            pnl_pct = ((position.current_price / position.entry_price) - 1) * 100
            position_key = position.entry_order_id or position.ticker
            if pnl_pct >= cfg.execution.trail_to_pct:
                new_stop = round(position.entry_price * (1 + cfg.execution.trail_stop_to_locked_profit_pct / 100), 2)
                if new_stop > position.stop_price:
                    position.stop_price = new_stop
                    self.gtt_manager.modify_gtt(position_key, new_stop)
            elif pnl_pct >= cfg.execution.trail_stop_at_pct:
                new_stop = round(position.entry_price, 2)
                if new_stop > position.stop_price:
                    position.stop_price = new_stop
                    self.gtt_manager.modify_gtt(position_key, new_stop)

    async def _process_gtt_triggers(self, state: AccountState) -> None:
        remaining: list[PositionState] = []
        trades = read_json(CONTEXT_DIR / "trades.json", [])
        for position in state.positions:
            key = position.entry_order_id or position.ticker
            gtt = self.gtt_manager.get_gtt(key)
            if gtt and gtt.status in {"triggered_stop", "triggered_target"}:
                exit_price = gtt.stop_price if gtt.status == "triggered_stop" else gtt.target_price
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
                    exit_reason="stop_loss" if gtt.status == "triggered_stop" else "target",
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
            else:
                remaining.append(position)
        state.positions = remaining
        write_json(CONTEXT_DIR / "trades.json", trades)

    async def poll(self) -> AccountState:
        if self._pause_active():
            await self.alerts.send_alert("Execution paused via PAUSE file", level="warning")
            return self._load_state()
        state = await self.reconciler.reconcile(self._load_state())
        expired = self.telegram_handler.expire_stale()
        for ticker in expired:
            await self.alerts.send_alert(f"{ticker} setup expired — not entered.", level="info")
        pending = self._load_pending()
        remaining: list[dict] = []
        for approval in pending:
            if approval.get("approved") is not True:
                remaining.append(approval)
                continue
            current_price = approval["entry_zone"]["high"]
            if not self._entry_still_valid(approval, current_price):
                await self.alerts.send_alert(
                    f"{approval['ticker']} approval expired due to price moving above the valid entry zone.",
                    level="warning",
                )
                continue
            result = self.order_tool.place_order(
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
            await self.alerts.send_alert(
                f"Entered {position.ticker}: qty {position.quantity} at {position.entry_price}",
                level="info",
            )
        self._save_pending(remaining)
        await self._handle_corporate_actions(state)
        await self._check_trailing(state)
        await self._process_gtt_triggers(state)
        self._save_state(state)
        self.log.info("Execution poll completed with {} open positions", len(state.positions))
        return state
