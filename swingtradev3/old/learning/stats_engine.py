from __future__ import annotations

import math

from swingtradev3.models import StatsSnapshot, TradeRecord
from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json


class StatsEngine:
    def __init__(self) -> None:
        self.trades_path = CONTEXT_DIR / "trades.json"
        self.stats_path = CONTEXT_DIR / "stats.json"

    def calculate(self) -> StatsSnapshot:
        payload = read_json(self.trades_path, [])
        trades = [TradeRecord.model_validate(item) for item in payload]
        if not trades:
            snapshot = StatsSnapshot()
            write_json(self.stats_path, snapshot.model_dump(mode="json"))
            return snapshot
        pnl_pcts = [trade.pnl_pct for trade in trades]
        winners = [value for value in pnl_pcts if value > 0]
        losers = [value for value in pnl_pcts if value <= 0]
        mean = sum(pnl_pcts) / len(pnl_pcts)
        variance = sum((value - mean) ** 2 for value in pnl_pcts) / max(len(pnl_pcts) - 1, 1)
        std = math.sqrt(variance)
        setup_totals: dict[str, list[float]] = {}
        for trade in trades:
            setup_totals.setdefault(trade.setup_type or "unknown", []).append(trade.pnl_pct)
        setup_scores = {k: sum(v) / len(v) for k, v in setup_totals.items()}
        snapshot = StatsSnapshot(
            win_rate=len(winners) / len(trades),
            sharpe=(mean / std) * math.sqrt(len(trades)) if std else 0.0,
            avg_winner_pct=sum(winners) / len(winners) if winners else 0.0,
            avg_loser_pct=sum(losers) / len(losers) if losers else 0.0,
            kelly_multiplier=max(mean / abs(min(sum(losers) / len(losers), -0.0001)), 0.0)
            if losers
            else 0.0,
            best_setup_type=max(setup_scores, key=setup_scores.get),
            worst_setup_type=min(setup_scores, key=setup_scores.get),
            trade_count=len(trades),
        )
        write_json(self.stats_path, snapshot.model_dump(mode="json"))
        return snapshot
