"""
Regime Adapter — Adjusts trading config based on market regime.

Applies risk overlays so the system automatically becomes conservative
in bear/choppy markets and aggressive in bull markets.

| Regime  | Position Size | Min Score | Stop Tightness | New Entries |
|---------|--------------|-----------|----------------|-------------|
| Bull    | 100%         | 7.0       | Normal         | ✅          |
| Neutral | 75%          | 7.5       | +10%           | ✅          |
| Bear    | 50%          | 8.0       | +20%           | ⚠️ Hi-conv  |
| Choppy  | 0%           | 9.0       | +30%           | ❌ Paused   |
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from config import cfg


class RegimeOverlay(BaseModel):
    """Adjustments for a specific regime."""
    position_size_pct: float  # % of normal size
    min_score: float          # minimum score for entry
    stop_tightness_pct: float # stop loss tightened by this %
    new_entries_allowed: bool
    label: str


# ─────────────────────────────────────────────────────────────
# Regime Definitions (from implementation plan)
# ─────────────────────────────────────────────────────────────

REGIME_OVERLAYS: dict[str, RegimeOverlay] = {
    "bull": RegimeOverlay(
        position_size_pct=100.0,
        min_score=7.0,
        stop_tightness_pct=0.0,
        new_entries_allowed=True,
        label="Bull — Full risk, normal operations",
    ),
    "neutral": RegimeOverlay(
        position_size_pct=75.0,
        min_score=7.5,
        stop_tightness_pct=10.0,
        new_entries_allowed=True,
        label="Neutral — Reduced size, tighter stops",
    ),
    "bear": RegimeOverlay(
        position_size_pct=50.0,
        min_score=8.0,
        stop_tightness_pct=20.0,
        new_entries_allowed=True,  # only high-conviction
        label="Bear — High-conviction only, tight stops",
    ),
    "choppy": RegimeOverlay(
        position_size_pct=0.0,
        min_score=9.0,
        stop_tightness_pct=30.0,
        new_entries_allowed=False,
        label="Choppy — No new entries, tightest stops",
    ),
}

# Aliases for regime detection output → overlay key
REGIME_ALIASES: dict[str, str] = {
    "bullish": "bull",
    "bearish": "bear",
    "sideways": "choppy",
    "recovery": "neutral",
    "rally": "bull",
    "correction": "bear",
    "distribution": "neutral",
    "accumulation": "neutral",
}


class RegimeAdaptiveConfig:
    """
    Wraps the base config and applies regime-dependent overlays.
    
    Usage:
        adapted = RegimeAdaptiveConfig("bear")
        max_qty = adapted.position_size(base_quantity=100)  # → 50
        min_score = adapted.min_entry_score()                # → 8.0
        stop = adapted.adjusted_stop(base_stop=95.0, entry=100.0)  # tighter
    """

    def __init__(self, regime: str) -> None:
        self._regime_key = self._normalize(regime)
        self._overlay = REGIME_OVERLAYS.get(self._regime_key, REGIME_OVERLAYS["neutral"])

    @staticmethod
    def _normalize(regime: str) -> str:
        """Map regime string to overlay key."""
        regime_lower = regime.lower().strip()
        if regime_lower in REGIME_OVERLAYS:
            return regime_lower
        return REGIME_ALIASES.get(regime_lower, "neutral")

    @property
    def regime(self) -> str:
        return self._regime_key

    @property
    def overlay(self) -> RegimeOverlay:
        return self._overlay

    @property
    def label(self) -> str:
        return self._overlay.label

    # ─── Applied Config Getters ───────────────────────────────

    def position_size(self, base_quantity: int) -> int:
        """Adjust position size for regime. Returns 0 if entries paused."""
        if not self._overlay.new_entries_allowed:
            return 0
        return max(1, round(base_quantity * self._overlay.position_size_pct / 100))

    def position_value(self, base_value: float) -> float:
        """Adjust position value (rupee amount) for regime."""
        if not self._overlay.new_entries_allowed:
            return 0.0
        return base_value * self._overlay.position_size_pct / 100

    def min_entry_score(self) -> float:
        """Minimum score required for entry in this regime."""
        return self._overlay.min_score

    def can_enter(self) -> bool:
        """Whether new entries are allowed at all."""
        return self._overlay.new_entries_allowed

    def adjusted_stop(self, base_stop: float, entry_price: float) -> float:
        """
        Tighten stop loss based on regime.
        Moves stop closer to entry by stop_tightness_pct of the original distance.
        
        Example: entry=100, base_stop=93 (7% stop), bear regime (+20% tighter)
        → distance = 7, tightened = 7 * 0.80 = 5.6 → new stop = 94.4
        """
        distance = abs(entry_price - base_stop)
        tightening = self._overlay.stop_tightness_pct / 100
        new_distance = distance * (1 - tightening)
        # Stop is below entry for long positions
        return entry_price - new_distance

    def to_dict(self) -> dict[str, Any]:
        """Serialize for dashboard / logging."""
        return {
            "regime": self._regime_key,
            "label": self._overlay.label,
            "position_size_pct": self._overlay.position_size_pct,
            "min_score": self._overlay.min_score,
            "stop_tightness_pct": self._overlay.stop_tightness_pct,
            "new_entries_allowed": self._overlay.new_entries_allowed,
        }
