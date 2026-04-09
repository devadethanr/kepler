from __future__ import annotations

from fastapi import APIRouter
from typing import Any

from tools.analysis.regime_detection import detect_regime
from models import RegimeState

router = APIRouter()

@router.get("", response_model=RegimeState)
async def get_regime():
    """Get current market regime."""
    result = detect_regime()
    return RegimeState(
        regime=result.get("regime", "choppy"),
        confidence=result.get("confidence", 0.0),
        volatility_state=result.get("volatility_state", "normal"),
        nifty_trend=result.get("trend_details", {}).get("trend_direction", "flat"),
        vix=result.get("vix"),
        fii_flow_direction="net_buy" if (result.get("fii_net_crore") or 0) > 0 else "net_sell",
    )
