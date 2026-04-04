from __future__ import annotations

from config import cfg


def capital_fraction_from_score(score: float) -> float:
    if score >= cfg.risk.confidence_sizing.high.min_score:
        return cfg.risk.confidence_sizing.high.capital_pct
    if score >= cfg.risk.confidence_sizing.medium.min_score:
        return cfg.risk.confidence_sizing.medium.capital_pct
    return 0.0


def calculate_position_size(available_capital: float, score: float, entry_price: float) -> int:
    fraction = capital_fraction_from_score(score)
    if not entry_price or entry_price <= 0:
        return 0
    return max(int((available_capital * fraction) // entry_price), 0)
