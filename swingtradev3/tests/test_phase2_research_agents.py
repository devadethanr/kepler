"""Tests for Phase 2.3: ADK Research Agents"""
import pytest
from unittest.mock import patch, MagicMock

from agents.research.filter_agent import FilterAgent
from agents.research.scorer_agent import ScorerAgent
from agents.research.pipeline import research_pipeline


class TestFilterAgent:
    @pytest.mark.asyncio
    async def test_fast_filter_below_ema(self):
        """Stock below 200 EMA should be filtered out."""
        agent = FilterAgent()
        import pandas as pd
        import numpy as np
        from config import cfg
        from data.kite_fetcher import KiteFetcher

        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=250, freq="B")
        close = np.linspace(100, 90, 250)  # Declining trend
        candles = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.random.randint(100000, 500000, 250),
        })
        
        kite_fetcher = KiteFetcher()
        
        with patch.object(kite_fetcher, "fetch_async", return_value=candles):
            passed, reason = await agent._fast_filter_async(kite_fetcher, cfg.research.filter, "TEST")
            assert passed is False
            assert "below_200ema" in reason

    @pytest.mark.asyncio
    async def test_fast_filter_above_ema(self):
        """Stock above 200 EMA with good volume should pass."""
        agent = FilterAgent()
        import pandas as pd
        import numpy as np
        from config import cfg
        from data.kite_fetcher import KiteFetcher

        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=250, freq="B")
        close = np.linspace(90, 120, 250)  # Rising trend
        volume = np.full(250, 500000)  # Consistent high volume
        candles = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": volume,
        })
        
        kite_fetcher = KiteFetcher()
        
        with patch.object(kite_fetcher, "fetch_async", return_value=candles):
            passed, reason = await agent._fast_filter_async(kite_fetcher, cfg.research.filter, "TEST")
            assert passed is True
            assert reason == "passed"


class TestScorerAgent:
    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        scorer = ScorerAgent()
        response = '''
        {
            "score": 8.0,
            "setup_type": "pullback",
            "entry_zone": {"low": 1000, "high": 1020},
            "stop_price": 980,
            "target_price": 1100,
            "holding_days": 15,
            "reasoning": "Test reasoning",
            "bull_case": ["reason1"],
            "bear_case": ["reason2"]
        }
        '''
        result = scorer._parse_response(response)
        assert result is not None
        assert result["score"] == 8.0
        assert result["setup_type"] == "pullback"

    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        scorer = ScorerAgent()
        response = '''```json
        {
            "score": 7.5,
            "setup_type": "breakout",
            "entry_zone": {"low": 500, "high": 510},
            "stop_price": 490,
            "target_price": 550,
            "holding_days": 10,
            "reasoning": "Test",
            "bull_case": [],
            "bear_case": []
        }
        ```'''
        result = scorer._parse_response(response)
        assert result is not None
        assert result["score"] == 7.5

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON returns None."""
        scorer = ScorerAgent()
        result = scorer._parse_response("not valid json")
        assert result is None


class TestResearchPipeline:
    def test_pipeline_init(self):
        """Test pipeline initializes correctly."""
        assert research_pipeline is not None
        assert len(research_pipeline.sub_agents) == 5
