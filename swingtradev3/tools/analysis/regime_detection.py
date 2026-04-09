"""
Regime Detection Tool
=====================
Tool wrapper for MarketRegimeDetector.
Exposes regime detection as an ADK-compatible tool.
Pure computation — no decisions.
"""
from __future__ import annotations

from typing import Any

from data.market_regime import MarketRegimeDetector
from data.institutional_flows import InstitutionalFlowsTool
from data.macro_indicators import MacroIndicatorsTool


_detector = MarketRegimeDetector()
_flows_tool = InstitutionalFlowsTool()
_macro_tool = MacroIndicatorsTool()


def detect_regime() -> dict[str, Any]:
    """
    Detect current market regime.

    Returns:
        {
            regime: "bull" | "bear" | "choppy" | "transition",
            confidence: 0.0-1.0,
            volatility_state: "low" | "normal" | "high",
            composite_score: float,
            signal_scores: {trend, vix, flows, breadth},
            trend_details: {...},
            vix: float | None,
            fii_net_crore: float | None,
            dii_net_crore: float | None,
        }
    """
    # Get macro data for VIX
    macro = _macro_tool.get_macro_indicators()
    vix = macro.get("india_vix")

    # Get FII/DII flows
    flows = _flows_tool.get_fii_dii()
    fii_net = flows.get("fii_net_crore")
    dii_net = flows.get("dii_net_crore")

    # Detect regime
    result = _detector.detect_regime(
        nifty_close=None,  # Would need Kite data
        vix=vix,
        fii_net=fii_net,
        dii_net=dii_net,
        advance_decline_ratio=None,
    )

    return result
