"""Tests for Phase 2.1: Data Layer"""

from types import SimpleNamespace

import pytest

from data.market_regime import MarketRegimeDetector
from data.institutional_flows import InstitutionalFlowsTool
from data.options_analyzer import OptionsAnalyzer
from data.macro_indicators import MacroIndicatorsTool
from data.news import NewsAggregator
from data.nifty200_loader import Nifty200Loader


class TestMarketRegimeDetector:
    def test_detect_regime_with_defaults(self):
        detector = MarketRegimeDetector()
        result = detector.detect_regime()
        assert "regime" in result
        assert result["regime"] in ["bull", "bear", "choppy", "transition"]
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0
        assert "volatility_state" in result
        assert result["volatility_state"] in ["low", "normal", "high"]
        assert result["signal_scores"]["trend"] == 0.5
        assert result["trend_details"]["status"] == "neutral_default"

    def test_detect_regime_bullish_signals(self):
        detector = MarketRegimeDetector()
        result = detector.detect_regime(
            vix=10.0,
            fii_net=2000.0,
            dii_net=1000.0,
            advance_decline_ratio=2.5,
        )
        assert result["regime"] in ["bull", "transition"]
        assert result["volatility_state"] == "low"

    def test_detect_regime_bearish_signals(self):
        detector = MarketRegimeDetector()
        result = detector.detect_regime(
            vix=30.0,
            fii_net=-3000.0,
            dii_net=-1000.0,
            advance_decline_ratio=0.2,
        )
        assert result["regime"] in ["bear", "choppy"]
        assert result["volatility_state"] == "high"

    def test_cached_regime(self):
        detector = MarketRegimeDetector()
        result1 = detector.detect_regime()
        result2 = detector.get_regime()
        assert result1["regime"] == result2["regime"]


class TestInstitutionalFlowsTool:
    def test_get_fii_dii(self):
        tool = InstitutionalFlowsTool()
        result = tool.get_fii_dii()
        assert "date" in result
        assert "fii_net_crore" in result or result.get("source") in ["not_configured", "cache"]

    def test_get_all(self):
        tool = InstitutionalFlowsTool()
        result = tool.get_all()
        assert "date" in result
        assert "fii_dii" in result


class TestOptionsAnalyzer:
    def test_analyze_options_bullish_pcr(self):
        analyzer = OptionsAnalyzer()
        result = analyzer.analyze_options(
            ticker="RELIANCE",
            pcr=1.4,
            iv=25.0,
            max_pain=2800.0,
            india_vix=15.0,
        )
        assert result["ticker"] == "RELIANCE"
        assert result["pcr"] == 1.4
        assert result["pcr_signal"] == "bullish"
        assert result["vix_regime"] in ["normal", "low"]  # 15.0 is borderline

    def test_analyze_options_bearish_pcr(self):
        analyzer = OptionsAnalyzer()
        result = analyzer.analyze_options(
            ticker="TCS",
            pcr=0.5,
            iv=30.0,
            india_vix=28.0,
        )
        assert result["pcr_signal"] == "bearish"
        assert result["vix_regime"] == "high"

    def test_analyze_options_unusual_activity(self):
        analyzer = OptionsAnalyzer()
        oi_data = [
            {"strike": 2800, "ce_oi": 1000, "pe_oi": 1500, "ce_change": -200, "pe_change": 100},
            {"strike": 2900, "ce_oi": 800, "pe_oi": 1200, "ce_change": -150, "pe_change": 50},
        ]
        result = analyzer.analyze_options(
            ticker="RELIANCE",
            pcr=1.2,
            oi_data=oi_data,
        )
        assert result["unusual_activity"] == "call_unwinding"


class TestMacroIndicatorsTool:
    def test_get_macro_indicators(self):
        tool = MacroIndicatorsTool()
        result = tool.get_macro_indicators()
        assert "date" in result
        assert "crude_usd" in result
        assert "usd_inr" in result
        assert "india_vix" in result

    def test_get_crude_trend(self):
        tool = MacroIndicatorsTool()
        tool.get_macro_indicators()
        trend = tool.get_crude_trend()
        assert trend in ["high", "moderate", "low", None]


class TestNewsAggregator:
    def test_search_news_tavily(self):
        aggregator = NewsAggregator()
        result = aggregator.search_news("RELIANCE stock news today")
        assert "query" in result
        assert "results" in result
        assert "source" in result

    def test_sweep_market_news(self):
        aggregator = NewsAggregator()
        result = aggregator.sweep_market_news()
        assert "results" in result

    def test_news_cache_uses_configured_minutes(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "news_cache.json"
        aggregator = NewsAggregator(cache_path=cache_path, ttl_minutes=1)
        calls = {"count": 0}

        def fake_tavily(*args, **kwargs):
            calls["count"] += 1
            return {
                "query": "RELIANCE stock news",
                "results": [
                    {"title": "Reliance Industries results", "url": "https://reuters.com/a"}
                ],
                "source": "fake",
            }

        monkeypatch.setattr(aggregator, "_from_official_feeds", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_bse_announcements", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_publisher_feeds", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_crawler_targets", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_tavily", fake_tavily)
        monkeypatch.setattr(aggregator, "_from_ddgs", lambda *args, **kwargs: None)

        first = aggregator.search_news("RELIANCE stock news")
        second = aggregator.search_news("RELIANCE stock news")

        assert first == second
        assert calls["count"] == 1

    def test_corrupt_news_cache_is_ignored(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "news_cache.json"
        cache_path.write_text('{"stale": true} trailing', encoding="utf-8")
        aggregator = NewsAggregator(cache_path=cache_path, ttl_minutes=1)

        def fake_tavily(*args, **kwargs):
            return {
                "query": "RELIANCE stock news",
                "results": [
                    {"title": "Reliance Industries results", "url": "https://reuters.com/a"}
                ],
                "source": "fake",
            }

        monkeypatch.setattr(aggregator, "_from_official_feeds", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_bse_announcements", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_publisher_feeds", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_crawler_targets", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_tavily", fake_tavily)
        monkeypatch.setattr(aggregator, "_from_ddgs", lambda *args, **kwargs: None)

        result = aggregator.search_news("RELIANCE stock news")

        assert result["source"] == "fake"
        assert "trailing" not in cache_path.read_text(encoding="utf-8")

    def test_filter_new_alerts_dedupes_same_url(self, tmp_path, monkeypatch):
        from data.news import core as module

        history_path = tmp_path / "news_alert_history.json"
        monkeypatch.setattr(module, "ALERT_HISTORY_PATH", history_path)
        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")
        headlines = [
            {"title": "Reliance Industries results", "url": "https://reuters.com/a"},
            {"title": "Reliance Industries results", "url": "https://reuters.com/a"},
        ]

        first = aggregator.filter_new_alerts("RELIANCE", headlines, cooldown_hours=24)
        second = aggregator.filter_new_alerts("RELIANCE", headlines, cooldown_hours=24)

        assert len(first) == 1
        assert second == []

    def test_filter_new_alerts_drops_items_for_other_companies(self, tmp_path, monkeypatch):
        from data.news import core as module

        history_path = tmp_path / "news_alert_history.json"
        monkeypatch.setattr(module, "ALERT_HISTORY_PATH", history_path)
        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")
        headlines = [
            {
                "title": "Gretex Corporate Services Limited",
                "url": "https://nsearchives.nseindia.com/corporate/gretex.pdf",
                "content": "Board meeting outcome",
            },
            {
                "title": "TCS announces board meeting outcome",
                "url": "https://nsearchives.nseindia.com/corporate/tcs.pdf",
                "content": "Tata Consultancy Services Limited update",
            },
        ]

        filtered = aggregator.filter_new_alerts(
            "TCS",
            headlines,
            cooldown_hours=24,
            company_name="Tata Consultancy Services",
        )

        assert [item["title"] for item in filtered] == ["TCS announces board meeting outcome"]

    def test_parse_published_at_handles_nse_ist_timestamp(self, tmp_path):
        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")

        item = aggregator._build_news_item(
            provider="nse_corporate_announcements_rss",
            source_type="official_filing",
            title="NSE company announcement",
            url="https://nsearchives.nseindia.com/corporate/sample.pdf",
            published_at="07-May-2026 07:58:31",
        )

        assert item["published_at_ist"] == "2026-05-07T07:58:31+05:30"
        assert item["published_at_utc"] == "2026-05-07T02:28:31+00:00"

    def test_rss_entries_without_links_get_unique_audit_urls(self, tmp_path, monkeypatch):
        import feedparser

        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")
        source = {
            "provider": "nse_corporate_announcements_rss",
            "source_type": "official_filing",
            "url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
        }

        monkeypatch.setattr(
            aggregator,
            "_request_url",
            lambda url: SimpleNamespace(content=b""),
        )
        monkeypatch.setattr(
            feedparser,
            "parse",
            lambda content: SimpleNamespace(
                entries=[
                    {
                        "title": "Company A board meeting",
                        "summary": "Board meeting update",
                        "published": "07-May-2026 07:00:00",
                    },
                    {
                        "title": "Company B analyst meet",
                        "summary": "Analyst meet update",
                        "published": "07-May-2026 07:00:00",
                    },
                ]
            ),
        )

        payload = aggregator._from_rss_sources(
            "Company",
            sources=(source,),
            source_name="official_feeds",
            max_results=5,
        )

        urls = [item["url"] for item in payload["results"]]
        assert len(urls) == 2
        assert len(set(urls)) == 2
        assert all("#news-" in url for url in urls)
        assert all(
            item["published_at_ist"] == "2026-05-07T07:00:00+05:30"
            for item in payload["results"]
        )

    def test_search_news_prioritizes_official_feeds(self, tmp_path, monkeypatch):
        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")
        official = {
            "query": "RELIANCE stock news",
            "results": [
                {
                    "provider": "nse_corporate_announcements_rss",
                    "title": "Reliance Industries board meeting update",
                    "url": "https://nseindia.com/announcements/reliance",
                    "content": "Reliance Industries official exchange update",
                }
            ],
            "source": "official_feeds",
        }

        monkeypatch.setattr(aggregator, "_from_official_feeds", lambda *args, **kwargs: official)
        monkeypatch.setattr(aggregator, "_from_bse_announcements", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_publisher_feeds", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_crawler_targets", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            aggregator,
            "_from_tavily",
            lambda *args, **kwargs: pytest.fail("Tavily should not run before official feed"),
        )
        monkeypatch.setattr(
            aggregator,
            "_from_ddgs",
            lambda *args, **kwargs: pytest.fail("DDGS should not run before official feed"),
        )

        result = aggregator.search_news("RELIANCE stock news", max_results=1)

        assert result["source"] == "official_feeds"
        assert result["results"][0]["provider"] == "nse_corporate_announcements_rss"

    def test_search_news_uses_publisher_feeds_before_search(self, tmp_path, monkeypatch):
        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")
        publisher = {
            "query": "TCS stock news",
            "results": [
                {
                    "provider": "economic_times_markets_rss",
                    "title": "TCS shares react to deal win",
                    "url": "https://economictimes.indiatimes.com/tcs",
                    "content": "TCS deal win",
                }
            ],
            "source": "publisher_feeds",
        }

        monkeypatch.setattr(aggregator, "_from_official_feeds", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_bse_announcements", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_publisher_feeds", lambda *args, **kwargs: publisher)
        monkeypatch.setattr(aggregator, "_from_crawler_targets", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            aggregator,
            "_from_tavily",
            lambda *args, **kwargs: pytest.fail("Tavily should not run before publisher feeds"),
        )

        result = aggregator.search_news("TCS stock news", max_results=1)

        assert result["source"] == "publisher_feeds"
        assert result["results"][0]["provider"] == "economic_times_markets_rss"

    def test_crawler_priority_uses_crawl4ai_before_firecrawl(self, tmp_path, monkeypatch):
        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")
        calls = []

        def missing(name):
            def extractor(url, *, query, provider):
                calls.append(name)
                return None

            return extractor

        def crawl4ai(url, *, query, provider):
            calls.append("crawl4ai")
            return {
                "provider": provider,
                "title": "Reliance JS-rendered news",
                "url": url,
                "content": "Reliance Industries order win",
            }

        monkeypatch.setattr(aggregator, "_from_static_url", missing("static"))
        monkeypatch.setattr(aggregator, "_from_trafilatura_url", missing("trafilatura"))
        monkeypatch.setattr(aggregator, "_from_crawl4ai_url", crawl4ai)
        monkeypatch.setattr(
            aggregator,
            "_from_firecrawl_url",
            lambda *args, **kwargs: pytest.fail("Firecrawl should run after Crawl4AI"),
        )

        item = aggregator._crawl_url_with_priority(
            "https://in.tradingview.com/symbols/NSE-RELIANCE/news/",
            query="RELIANCE stock news",
            provider="tradingview_crawler",
        )

        assert item["provider"] == "tradingview_crawler"
        assert calls == ["static", "trafilatura", "crawl4ai"]

    def test_search_stock_news_uses_crawler_when_search_empty(self, tmp_path, monkeypatch):
        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")

        monkeypatch.setattr(aggregator, "_from_upstox_news", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            aggregator,
            "search_news",
            lambda *args, **kwargs: {"query": args[0], "results": [], "source": "not_configured"},
        )
        monkeypatch.setattr(
            aggregator,
            "_from_crawler_targets",
            lambda *args, **kwargs: {
                "query": args[0],
                "results": [
                    {
                        "provider": "groww_crawler",
                        "title": "Reliance Industries wins new contract",
                        "url": "https://groww.in/stocks/reliance-industries",
                        "content": "Reliance Industries contract update",
                    }
                ],
                "source": "crawler_targets",
            },
        )

        result = aggregator.search_stock_news("RELIANCE", "Reliance Industries")

        assert result["source"] == "crawler_targets"
        assert result["results"][0]["domain"] == "groww.in"

    def test_search_stock_news_filters_loose_company_suffix_matches(self, tmp_path, monkeypatch):
        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")

        monkeypatch.setattr(aggregator, "_from_upstox_news", lambda *args, **kwargs: None)
        monkeypatch.setattr(aggregator, "_from_crawler_targets", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            aggregator,
            "search_news",
            lambda *args, **kwargs: {
                "query": args[0],
                "results": [
                    {
                        "provider": "nse_corporate_announcements_rss",
                        "source_type": "official_filing",
                        "title": "Gretex Corporate Services Limited",
                        "url": "https://nsearchives.nseindia.com/corporate/gretex.pdf",
                        "content": "Board meeting outcome",
                    },
                    {
                        "provider": "nse_corporate_announcements_rss",
                        "source_type": "official_filing",
                        "title": "Tata Consultancy Services Limited",
                        "url": "https://nsearchives.nseindia.com/corporate/tcs.pdf",
                        "content": "Dividend board meeting outcome",
                    },
                ],
                "source": "official_feeds",
            },
        )

        result = aggregator.search_stock_news("TCS", "Tata Consultancy Services")

        assert [item["title"] for item in result["results"]] == [
            "Tata Consultancy Services Limited"
        ]

    def test_build_market_digest_groups_tickers_and_general_news(self, tmp_path, monkeypatch):
        from data.news import core as module

        history_path = tmp_path / "news_alert_history.json"
        monkeypatch.setattr(module, "ALERT_HISTORY_PATH", history_path)
        aggregator = NewsAggregator(cache_path=tmp_path / "news_cache.json")
        aggregator._universe_entries = [
            {"ticker": "RELIANCE", "name": "Reliance Industries"},
            {"ticker": "TCS", "name": "Tata Consultancy Services"},
        ]
        payload = {
            "query": "Indian stock market news",
            "results": [
                {
                    "title": "Reliance Industries Q4 profit beats estimates",
                    "url": "https://example.com/reliance",
                    "content": "Reliance Industries profit rises",
                },
                {
                    "title": "RBI policy keeps market cautious",
                    "url": "https://example.com/rbi-policy",
                    "content": "Macro liquidity and rates update",
                    "category": "macro",
                },
            ],
            "source": "multi_source",
        }

        digest = aggregator.build_market_digest(payload, cooldown_hours=24)
        second = aggregator.build_market_digest(payload, cooldown_hours=24)

        assert digest["item_count"] == 2
        assert digest["ticker_groups"][0]["ticker"] == "RELIANCE"
        assert digest["general"][0]["title"] == "RBI policy keeps market cautious"
        assert second["item_count"] == 0


class TestNifty200Loader:
    def test_load_universe(self):
        loader = Nifty200Loader()
        tickers = loader.load()
        assert len(tickers) == 200
        assert "RELIANCE" in tickers
        assert "TCS" in tickers

    def test_name_for(self):
        loader = Nifty200Loader()
        name = loader.name_for("RELIANCE")
        assert isinstance(name, str)
        assert len(name) > 0
