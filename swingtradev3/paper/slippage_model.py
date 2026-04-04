from __future__ import annotations

from config import cfg


def apply_slippage(price: float, side: str, slippage_pct: float | None = None) -> float:
    pct = cfg.backtest.slippage_pct if slippage_pct is None else slippage_pct
    multiplier = 1 + pct if side.lower() == "buy" else 1 - pct
    return round(price * multiplier, 2)
