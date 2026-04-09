from __future__ import annotations

import json
from typing import Any

from google.adk.agents import BaseAgent
from google.adk.events import Event

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json, write_json
from models import TradeRecord, StatsSnapshot


class StatsAgent(BaseAgent):
    """
    Calculates monthly stats and Kelly sizing criteria from closed trades.
    """
    def __init__(self, name: str = "StatsAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> Event:
        trades_payload = read_json(CONTEXT_DIR / "trades.json", [])
        if not trades_payload:
            return Event(author=self.name, content={"msg": "No closed trades"})
            
        trades = [TradeRecord.model_validate(t) for t in trades_payload]
        
        wins = [t.pnl_abs for t in trades if t.pnl_abs > 0]
        losses = [abs(t.pnl_abs) for t in trades if t.pnl_abs < 0]
        
        trade_count = len(trades)
        win_rate = len(wins) / trade_count if trade_count > 0 else 0.0
        
        avg_winner = sum(wins) / len(wins) if wins else 0.0
        avg_loser = sum(losses) / len(losses) if losses else 0.0
        
        # Kelly Multiplier = W - [(1 - W) / R]
        # where W = win rate, R = Win/Loss ratio (avg_winner / avg_loser)
        kelly = 0.0
        if avg_loser > 0:
            r = avg_winner / avg_loser
            kelly = win_rate - ((1.0 - win_rate) / r)
            
        # Simplified sharpe approximation
        sharpe = 0.0
        
        # Setup type stats
        setup_wins = {}
        setup_counts = {}
        for t in trades:
            st = t.setup_type or "unknown"
            setup_counts[st] = setup_counts.get(st, 0) + 1
            if t.pnl_abs > 0:
                setup_wins[st] = setup_wins.get(st, 0) + 1
                
        best_setup = None
        worst_setup = None
        best_win_rate = -1.0
        worst_win_rate = 2.0
        
        for st, count in setup_counts.items():
            if count >= 3:
                wr = setup_wins.get(st, 0) / count
                if wr > best_win_rate:
                    best_win_rate = wr
                    best_setup = st
                if wr < worst_win_rate:
                    worst_win_rate = wr
                    worst_setup = st
                    
        stats = StatsSnapshot(
            win_rate=round(win_rate, 4),
            sharpe=round(sharpe, 4),
            avg_winner_pct=round(avg_winner, 4),
            avg_loser_pct=round(avg_loser, 4),
            kelly_multiplier=round(max(0.0, kelly), 4),
            best_setup_type=best_setup,
            worst_setup_type=worst_setup,
            trade_count=trade_count,
        )
        
        write_json(CONTEXT_DIR / "stats.json", stats.model_dump(mode="json"))
        
        return Event(author=self.name, content={"msg": "Stats updated", "stats": stats.model_dump(mode="json")})

stats_agent = StatsAgent()
