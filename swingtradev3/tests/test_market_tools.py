from __future__ import annotations

from datetime import date
from pathlib import Path

from swingtradev3.tools.market.fii_dii_data import FiiDiiDataTool
from swingtradev3.tools.market.fundamental_data import FundamentalDataTool
from swingtradev3.tools.market.news_search import NewsSearchTool


def test_news_search_uses_cached_payload(tmp_path: Path) -> None:
    tool = NewsSearchTool(cache_path=tmp_path / "news_cache.json")
    expected = {"query": "INFY news", "results": [{"title": "A"}], "source": "cached"}
    tool._store("INFY news", expected)

    payload = tool.search_news("INFY news")

    assert payload == expected


def test_fii_dii_parse_csv_extracts_nets() -> None:
    csv_payload = (
        "Category,Buy Value,Sell Value,Net Value,Date\n"
        "FII/FPI,1000,900,100,2026-03-24\n"
        "DII,800,950,-150,2026-03-24\n"
    )

    parsed = FiiDiiDataTool._parse_csv(csv_payload)

    assert parsed["fii_net_crore"] == 100.0
    assert parsed["dii_net_crore"] == -150.0
    assert parsed["date"] == "2026-03-24"
    assert len(parsed["rows"]) == 2


def test_fundamental_data_returns_fresh_cache_without_refresh(tmp_path: Path) -> None:
    tool = FundamentalDataTool(cache_path=tmp_path / "fundamentals_cache.json")
    tool._write_cache(
        {
            "INFY": {
                "ticker": "INFY",
                "pe_ratio": 25.0,
                "market_cap_cr": 100000.0,
                "source": "cache",
                "as_of": date.today().isoformat(),
                "is_stale": False,
            }
        }
    )

    payload = tool.get_fundamentals("INFY")

    assert payload["ticker"] == "INFY"
    assert payload["pe_ratio"] == 25.0
    assert payload["is_stale"] is False


def test_fundamental_data_firecrawl_parser_extracts_values(tmp_path: Path, monkeypatch) -> None:
    tool = FundamentalDataTool(cache_path=tmp_path / "fundamentals_cache.json")

    class StubResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "data": {
                    "markdown": (
                        "Market Cap\n123,456\n"
                        "Stock P/E\n21.4\n"
                        "Dividend Yield\n1.8\n"
                        "Promoter holding\n54.2\n"
                        "Pledged percentage\n0.0\n"
                    )
                }
            }

    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr("requests.post", lambda *args, **kwargs: StubResponse())

    payload = tool._from_firecrawl("INFY")

    assert payload["market_cap_cr"] == 123456.0
    assert payload["pe_ratio"] == 21.4
    assert payload["dividend_yield"] == 1.8
    assert payload["promoter_holding_pct"] == 54.2
