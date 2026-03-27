from __future__ import annotations

import pytest

from swingtradev3.auth.kite.client import (
    build_kite_client,
    fetch_ltp,
    fetch_historical_data,
    has_kite_session,
)
from swingtradev3.data.kite_fetcher import KiteFetcher
from swingtradev3.integrations.kite.mcp_client import KiteMCPClient
from swingtradev3.config import cfg


class TestKiteDirectEndpoints:
    """Test direct Kite API endpoints with paid app."""

    @pytest.fixture(autouse=True)
    def check_session(self):
        """Skip tests if no Kite session is available or token is invalid."""
        if not has_kite_session():
            pytest.skip("No Kite session available")
        # Try a quick test call to verify token is valid
        try:
            fetch_ltp("NSE", "RELIANCE")
        except Exception as e:
            if (
                "api_key" in str(e).lower()
                or "access_token" in str(e).lower()
                or "token" in str(e).lower()
            ):
                pytest.skip(f"Kite token invalid - needs re-auth: {e}")
            raise

    def test_kite_ltp_fetch_nifty50(self):
        """Test fetching LTP for Nifty 50 tickers."""
        test_tickers = ["RELIANCE", "INFY", "HDFCBANK", "TCS", "ICICIBANK"]

        for ticker in test_tickers:
            price = fetch_ltp("NSE", ticker)
            assert price > 0, f"Invalid price for {ticker}: {price}"
            print(f"{ticker}: ₹{price}")

    def test_kite_historical_data_30_days(self):
        """Test fetching 30 days of historical data."""
        test_tickers = ["RELIANCE", "INFY"]

        for ticker in test_tickers:
            candles = fetch_historical_data(
                ticker,
                exchange="NSE",
                interval="day",
                lookback_days=30,
            )
            assert candles is not None, f"Failed to fetch data for {ticker}"
            assert len(candles) > 0, f"Empty candles for {ticker}"

            # Check candle structure
            first_candle = candles[0]
            assert "date" in first_candle, f"Missing date in candle for {ticker}"
            assert "open" in first_candle, f"Missing open in candle for {ticker}"
            assert "high" in first_candle, f"Missing high in candle for {ticker}"
            assert "low" in first_candle, f"Missing low in candle for {ticker}"
            assert "close" in first_candle, f"Missing close in candle for {ticker}"
            assert "volume" in first_candle, f"Missing volume in candle for {ticker}"

            print(
                f"{ticker}: {len(candles)} candles, last close: ₹{candles[-1]['close']}"
            )

    def test_kite_historical_data_weekly(self):
        """Test fetching weekly historical data."""
        candles = fetch_historical_data(
            "RELIANCE",
            exchange="NSE",
            interval="week",
            lookback_days=90,
        )
        assert candles is not None
        assert len(candles) > 0
        print(f"RELIANCE weekly: {len(candles)} candles")

    def test_kite_quote_fetch(self):
        """Test fetching full quote for instruments."""
        client = build_kite_client()
        instruments = ["NSE:RELIANCE", "NSE:INFY"]
        quotes = client.quote(instruments)

        assert quotes is not None
        for inst in instruments:
            assert inst in quotes, f"Missing quote for {inst}"
            data = quotes[inst]
            assert "last_price" in data, f"Missing last_price for {inst}"
            assert data["last_price"] > 0, f"Invalid last_price for {inst}"
            print(f"{inst}: ₹{data['last_price']}")


class TestKiteFetcherN200:
    """Test KiteFetcher with Nifty 200 tickers."""

    @pytest.fixture(autouse=True)
    def check_session(self):
        """Skip tests if no Kite session is available or token is invalid."""
        if not has_kite_session():
            pytest.skip("No Kite session available")
        # Try a quick test call to verify token is valid
        try:
            fetch_ltp("NSE", "RELIANCE")
        except Exception as e:
            if (
                "api_key" in str(e).lower()
                or "access_token" in str(e).lower()
                or "token" in str(e).lower()
            ):
                pytest.skip(f"Kite token invalid - needs re-auth: {e}")
            raise

    @pytest.fixture
    def fetcher(self):
        return KiteFetcher()

    def test_kite_fetcher_n200_ticker(self, fetcher):
        """Test fetching candles for a Nifty 200 ticker."""
        # Use a known N200 ticker
        ticker = "AUBANK"  # AU Small Finance Bank

        df = fetcher.fetch(ticker, interval="day")

        assert df is not None
        assert len(df) > 0
        assert "close" in df.columns
        assert "volume" in df.columns
        print(f"AUBANK: {len(df)} candles, last close: ₹{df['close'].iloc[-1]}")

    def test_kite_fetcher_n50_ticker(self, fetcher):
        """Test fetching candles for a Nifty 50 ticker."""
        ticker = "BAJFINANCE"

        df = fetcher.fetch(ticker, interval="day")

        assert df is not None
        assert len(df) > 0
        print(f"BAJFINANCE: {len(df)} candles, last close: ₹{df['close'].iloc[-1]}")


class TestMCPFallback:
    """Test MCP fallback for data endpoints."""

    @pytest.fixture
    def mcp_client(self):
        return KiteMCPClient()

    @pytest.mark.asyncio
    async def test_mcp_instrument_search(self, mcp_client):
        """Test MCP instrument search fallback."""
        result = await mcp_client.call_tool(
            "search_instruments",
            {"query": "RELIANCE"},
        )

        assert result is not None
        # MCP returns structured content
        content = result.get("content", [])
        assert len(content) > 0, "No results from MCP search"
        print(f"MCP search results: {len(content)} instruments")

    @pytest.mark.asyncio
    async def test_mcp_historical_fallback(self, mcp_client):
        """Test MCP historical data fallback."""
        from swingtradev3.auth.kite.client import resolve_instrument_token

        # Get instrument token - will fail if no session
        try:
            token = resolve_instrument_token("RELIANCE", "NSE")
        except Exception:
            pytest.skip("MCP needs access token in environment or session")

        # Test MCP with proper datetime format
        result = await mcp_client.call_tool(
            "get_historical_data",
            {
                "instrument_token": token,
                "from_date": "2026-03-01 00:00:00",
                "to_date": "2026-03-28 00:00:00",
                "interval": "day",
            },
        )

        # Check if MCP is logged in
        content = result.get("content", [])
        text = content[0].get("text", "") if content else ""
        if "log in first" in text.lower():
            pytest.skip("MCP server requires login - needs KITE_ACCESS_TOKEN env var")

        candles = result.get("candles") or result.get("data") or []
        assert len(candles) > 0, "No candles from MCP"

        # Check candle structure
        first_candle = candles[0]
        assert len(first_candle) >= 5, "Incomplete candle data"
        print(f"MCP historical: {len(candles)} candles")


class TestLiveModeDataPath:
    """Test the full live mode data path."""

    @pytest.fixture(autouse=True)
    def check_session(self):
        """Skip tests if no Kite session is available or token is invalid."""
        if not has_kite_session():
            pytest.skip("No Kite session available")
        # Try a quick test call to verify token is valid
        try:
            fetch_ltp("NSE", "RELIANCE")
        except Exception as e:
            if (
                "api_key" in str(e).lower()
                or "access_token" in str(e).lower()
                or "token" in str(e).lower()
            ):
                pytest.skip(f"Kite token invalid - needs re-auth: {e}")
            raise

    def test_market_data_tool_with_live_data(self):
        """Test that market_data tool works with live Kite data."""
        from swingtradev3.tools.market.market_data import MarketDataTool

        tool = MarketDataTool()

        # This should use Kite directly in live mode
        data = tool.get_eod_data("RELIANCE")

        assert data is not None
        assert "close" in data
        assert data["close"] > 0
        print(f"Market data for RELIANCE: close ₹{data['close']}")
