from __future__ import annotations

from data.news.parsers import (
    extract_tickers_from_text,
    parse_bse_announcements,
    parse_groww_newsdata,
    parse_json_ld_item_list,
    parse_source_specific_html,
    parse_upstox_news,
)


def test_parse_upstox_news_maps_provider_payload():
    payload = {
        "status": "success",
        "data": {
            "NSE_EQ|INE002A01018": [
                {
                    "heading": "Reliance Industries wins new order",
                    "summary": "Order book improves after a large contract.",
                    "article_link": "https://upstox.com/news/reliance/article-1/",
                    "published_time": 1776251261821,
                }
            ]
        },
    }

    rows = parse_upstox_news(payload)

    assert rows[0]["title"] == "Reliance Industries wins new order"
    assert rows[0]["instrument_key"] == "NSE_EQ|INE002A01018"
    assert rows[0]["category"] == "order_win"
    assert rows[0]["published_at"].endswith("+00:00")


def test_parse_bse_announcements_dedupable_newsid_shape():
    payload = {
        "Table": [
            {
                "NEWSID": "abc-1",
                "SCRIP_CD": "500325",
                "SLONGNAME": "Reliance Industries Ltd",
                "NEWS_SUB": "Board Meeting Intimation",
                "HEADLINE": "Board to consider dividend",
                "ATTACHMENTNAME": "reliance.pdf",
                "DissemDT": "2026-05-06T09:15:00",
            }
        ]
    }

    rows = parse_bse_announcements(payload)

    assert rows[0]["source_id"] == "abc-1"
    assert rows[0]["company_names"] == ["Reliance Industries Ltd"]
    assert rows[0]["category"] == "corporate_action"
    assert rows[0]["url"].endswith("/reliance.pdf")


def test_parse_groww_newsdata_extracts_embedded_items():
    html = """
    <script>
      window.__DATA__ = {"newsData":[{"title":"TCS signs AI deal","summary":"Large deal",
      "url":"/news/tcs-ai","source":"Groww","pubDate":"2026-05-06T08:00:00+05:30"}]};
    </script>
    """

    rows = parse_groww_newsdata(html, "https://groww.in")

    assert rows[0]["title"] == "TCS signs AI deal"
    assert rows[0]["url"] == "https://groww.in/news/tcs-ai"
    assert rows[0]["category"] == "order_win"


def test_parse_moneycontrol_json_ld_item_list():
    html = """
    <script type="application/ld+json">
    {"@type":"ItemList","itemListElement":[
      {"item":{"name":"Infosys Q4 results preview","url":"/news/infosys-results"}}
    ]}
    </script>
    """

    rows = parse_json_ld_item_list(html, "https://www.moneycontrol.com")

    assert rows[0]["title"] == "Infosys Q4 results preview"
    assert rows[0]["url"] == "https://www.moneycontrol.com/news/infosys-results"
    assert rows[0]["category"] == "earnings"


def test_source_specific_html_falls_back_to_article_links():
    html = '<a href="/market/stocks/reliance-order-win">Reliance wins large contract</a>'

    rows = parse_source_specific_html("cnbctv18_crawler", html, "https://www.cnbctv18.com")

    assert rows[0]["url"] == "https://www.cnbctv18.com/market/stocks/reliance-order-win"
    assert rows[0]["category"] == "order_win"


def test_extract_tickers_from_text_uses_company_aliases():
    universe = [
        {"ticker": "RELIANCE", "name": "Reliance Industries Ltd."},
        {"ticker": "TCS", "name": "Tata Consultancy Services Ltd."},
    ]

    assert extract_tickers_from_text("Tata Consultancy Services signs deal", universe) == ["TCS"]
