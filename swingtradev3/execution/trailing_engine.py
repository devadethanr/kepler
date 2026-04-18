from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from auth.kite.client import fetch_ltp, has_kite_session
from config import cfg
from memory.db import session_scope
from memory.repositories import MemoryRepository
from models import AccountState, PositionState
from tools.execution.alerts import AlertsTool
from tools.execution.gtt_manager import GTTManager


def _now() -> datetime:
    return datetime.now()


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


class TrailingEngine:
    def __init__(
        self,
        *,
        gtt_manager: GTTManager | None = None,
        alerts_tool: AlertsTool | None = None,
    ) -> None:
        self.gtt_manager = gtt_manager or GTTManager()
        self.alerts_tool = alerts_tool or AlertsTool()

    async def run_once(
        self,
        *,
        quote_provider: Callable[[str], dict[str, Any] | None] | None = None,
    ) -> dict[str, int]:
        if not cfg.execution.enable_trailing:
            return {"positions": 0, "modified": 0}

        with session_scope() as session:
            repo = MemoryRepository(session)
            state = AccountState.model_validate(repo.get_account_state_payload())

        modified = 0
        updated_positions: list[PositionState] = []
        for position in state.positions:
            updated = await self._trail_position(position, quote_provider=quote_provider)
            updated_positions.append(updated)
            if updated.stop_price != position.stop_price:
                modified += 1

        if modified or any(
            updated.current_price != original.current_price
            or updated.lifecycle_state != original.lifecycle_state
            for original, updated in zip(state.positions, updated_positions, strict=False)
        ):
            next_state = state.model_copy(update={"positions": updated_positions})
            with session_scope() as session:
                repo = MemoryRepository(session)
                repo.replace_account_state(next_state.model_dump(mode="json"), source="trailing_engine")

        return {"positions": len(state.positions), "modified": modified}

    async def _trail_position(
        self,
        position: PositionState,
        *,
        quote_provider: Callable[[str], dict[str, Any] | None] | None,
    ) -> PositionState:
        if not position.oco_gtt_id or position.lifecycle_state != "open":
            return position

        last_price = self._resolve_last_price(position.ticker, quote_provider)
        if last_price is None or last_price <= 0:
            return position

        desired_stop = self._desired_stop(position, last_price)
        if desired_stop is None:
            return position.model_copy(update={"current_price": last_price})

        with session_scope() as session:
            repo = MemoryRepository(session)
            trigger = repo.get_protective_trigger(str(position.oco_gtt_id))
        if trigger is not None and trigger["status"] not in {"active", "recreate_required"}:
            return position.model_copy(update={"current_price": last_price})

        min_step = max(position.entry_price * (cfg.execution.trail_min_step_pct / 100.0), 0.01)
        hysteresis = max(position.entry_price * (cfg.execution.trail_hysteresis_pct / 100.0), min_step)
        if desired_stop <= position.stop_price or (desired_stop - position.stop_price) < hysteresis:
            return position.model_copy(update={"current_price": last_price})

        if trigger is not None:
            last_modified = _parse_datetime(trigger["payload"].get("last_modified_at"))
            if last_modified is not None:
                cooldown = timedelta(seconds=cfg.execution.trail_modify_cooldown_seconds)
                if _now() - last_modified < cooldown:
                    return position.model_copy(update={"current_price": last_price})

        await self.gtt_manager.modify_gtt_async(
            str(position.oco_gtt_id),
            desired_stop,
            ticker=position.ticker,
            target_price=position.target_price,
            quantity=position.quantity,
        )

        now_iso = _now().isoformat()
        with session_scope() as session:
            repo = MemoryRepository(session)
            trigger = repo.get_protective_trigger(str(position.oco_gtt_id))
            payload = dict(trigger["payload"]) if trigger is not None else {"ticker": position.ticker.upper()}
            payload.update(
                {
                    "stop_price": desired_stop,
                    "target_price": position.target_price,
                    "quantity": position.quantity,
                    "last_modified_at": now_iso,
                    "last_seen_price": last_price,
                    "modification_count": int(payload.get("modification_count") or 0) + 1,
                    "broker_status": "active",
                }
            )
            repo.upsert_protective_trigger(
                protective_trigger_id=str(position.oco_gtt_id),
                position_id=position.ticker.upper(),
                ticker=position.ticker.upper(),
                status="active",
                payload=payload,
                source="trailing_engine",
            )
            repo.append_execution_event(
                event_type="protective_trigger_modified",
                entity_type="protective_trigger",
                entity_id=str(position.oco_gtt_id),
                source="trailing_engine",
                payload={
                    "ticker": position.ticker.upper(),
                    "new_stop": desired_stop,
                    "target_price": position.target_price,
                    "last_price": last_price,
                },
            )

        try:
            from api.tasks.event_bus import BusEvent, EventType, event_bus

            await event_bus.publish(
                BusEvent(
                    type=EventType.STOP_TRAILED,
                    payload={
                        "ticker": position.ticker.upper(),
                        "new_stop": desired_stop,
                        "last_price": last_price,
                    },
                    source="trailing_engine",
                )
            )
        except Exception:
            pass

        await self.alerts_tool.send_alert(
            f"📈 Trailed stop for {position.ticker.upper()} to {desired_stop:.2f}"
        )
        return position.model_copy(update={"current_price": last_price, "stop_price": desired_stop})

    def _desired_stop(self, position: PositionState, last_price: float) -> float | None:
        pnl_pct = ((last_price / position.entry_price) - 1) * 100 if position.entry_price else 0.0
        if pnl_pct >= cfg.execution.trail_to_pct:
            return round(
                position.entry_price
                * (1 + (cfg.execution.trail_stop_to_locked_profit_pct / 100.0)),
                2,
            )
        if pnl_pct >= cfg.execution.trail_stop_at_pct:
            return round(position.entry_price, 2)
        return None

    def _resolve_last_price(
        self,
        ticker: str,
        quote_provider: Callable[[str], dict[str, Any] | None] | None,
    ) -> float | None:
        if quote_provider is not None:
            tick = quote_provider(ticker)
            if isinstance(tick, dict) and tick.get("last_price") not in (None, ""):
                return float(tick["last_price"])
        if has_kite_session():
            try:
                return float(fetch_ltp(cfg.trading.exchange, ticker))
            except Exception:
                return None
        return None
