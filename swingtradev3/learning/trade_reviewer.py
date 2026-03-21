from __future__ import annotations

from datetime import datetime

from swingtradev3.models import TradeObservation, TradeRecord
from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json


class TradeReviewer:
    def __init__(self) -> None:
        self.path = CONTEXT_DIR / "trade_observations.json"

    def review(self, trade: TradeRecord) -> TradeObservation:
        thesis_held = trade.exit_reason == "target"
        observation = TradeObservation(
            trade_id=trade.trade_id,
            ticker=trade.ticker,
            observation=f"Trade exited via {trade.exit_reason}. PnL {trade.pnl_pct:.2f}%.",
            thesis_held=thesis_held,
            exit_reason=trade.exit_reason,
            created_at=datetime.utcnow(),
        )
        payload = read_json(self.path, [])
        payload.append(observation.model_dump(mode="json"))
        write_json(self.path, payload)
        return observation
