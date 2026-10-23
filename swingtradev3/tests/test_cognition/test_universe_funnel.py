from __future__ import annotations

from cognition.slow_brain.universe_funnel import UniverseFunnel
from cognition.types import RegimeSynthesis


def test_universe_funnel_caps_sector_and_routes_top_candidates():
    results = [
        {"ticker": "A", "score": 9.1, "setup_type": "breakout", "sector": "IT"},
        {"ticker": "B", "score": 8.9, "setup_type": "breakout", "sector": "IT"},
        {"ticker": "C", "score": 8.8, "setup_type": "breakout", "sector": "IT"},
        {"ticker": "D", "score": 8.7, "setup_type": "pullback", "sector": "Bank"},
        {"ticker": "E", "score": 6.5, "setup_type": "pullback", "sector": "Auto"},
    ]

    funnel = UniverseFunnel(max_candidates=4, full_debate_candidates=2).select(
        run_id="phase13-test",
        scan_results=results,
        regime=RegimeSynthesis(regime="bull"),
    )

    assert [item.ticker for item in funnel.candidates] == ["A", "B", "D"]
    assert [item.route for item in funnel.candidates] == [
        "full_debate",
        "full_debate",
        "lightweight",
    ]
    assert any(item.ticker == "C" and item.reason == "sector_cap:IT" for item in funnel.skipped)
    assert any(item.ticker == "E" and item.reason.startswith("score_below") for item in funnel.skipped)

