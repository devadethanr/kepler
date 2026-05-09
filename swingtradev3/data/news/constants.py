from __future__ import annotations

from zoneinfo import ZoneInfo

from paths import CONTEXT_DIR

ALERT_HISTORY_PATH = CONTEXT_DIR / "news_alert_history.json"
NEWS_ITEMS_PATH = CONTEXT_DIR / "news_items.json"
NEWS_PROVIDER_HEALTH_PATH = CONTEXT_DIR / "news_provider_health.json"
IST_ZONE = ZoneInfo("Asia/Kolkata")
REQUEST_TIMEOUT_SECONDS = 8
NEWS_AUDIT_MAX_ITEMS = 500

OFFICIAL_RSS_SOURCES: tuple[dict[str, str], ...] = (
    {
        "provider": "nse_corporate_announcements_rss",
        "source_type": "official_filing",
        "url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
    },
    {
        "provider": "sebi_rss",
        "source_type": "regulator",
        "url": "https://www.sebi.gov.in/sebirss.xml",
    },
    {
        "provider": "rbi_press_releases_rss",
        "source_type": "regulator",
        "url": "https://rbi.org.in/pressreleases_rss.xml",
    },
    {
        "provider": "pib_rss",
        "source_type": "regulator",
        "url": "https://www.pib.gov.in/ViewRss.aspx?lang=1&reg=22",
    },
    {
        "provider": "zerodha_zconnect_rss",
        "source_type": "broker_api",
        "url": "https://zerodha.com/z-connect/feed",
    },
)

PUBLISHER_RSS_SOURCES: tuple[dict[str, str], ...] = (
    {
        "provider": "moneycontrol_rss",
        "source_type": "publisher_rss",
        "url": "https://www.moneycontrol.com/rss/MCtopnews.xml",
    },
    {
        "provider": "economic_times_markets_rss",
        "source_type": "publisher_rss",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    },
    {
        "provider": "google_news_market_rss",
        "source_type": "publisher_rss",
        "url": (
            "https://news.google.com/rss/search?"
            "q=Indian%20stock%20market%20NSE%20BSE&hl=en-IN&gl=IN&ceid=IN:en"
        ),
    },
)

GENERIC_NEWS_TERMS = {
    "24",
    "200",
    "bse",
    "current",
    "india",
    "indian",
    "latest",
    "market",
    "markets",
    "news",
    "nifty",
    "nse",
    "stock",
    "stocks",
    "today",
    "week",
}

PUBLISHER_PAGE_TARGETS: tuple[dict[str, str], ...] = (
    {
        "provider": "moneycontrol_tag_crawler",
        "url": "https://www.moneycontrol.com/news/tags/-stocks.html",
    },
    {
        "provider": "etmarkets_crawler",
        "url": "https://economictimes.indiatimes.com/markets/stocks/news",
    },
    {"provider": "ndtvprofit_crawler", "url": "https://www.ndtvprofit.com/markets/stocks/"},
    {"provider": "cnbctv18_crawler", "url": "https://www.cnbctv18.com/market/stocks/"},
    {
        "provider": "business_standard_crawler",
        "url": "https://www.business-standard.com/markets/news",
    },
    {"provider": "livemint_crawler", "url": "https://www.livemint.com/market/stock-market-news"},
    {
        "provider": "businessline_crawler",
        "url": "https://www.thehindubusinessline.com/markets/stock-markets/",
    },
    {"provider": "financial_express_crawler", "url": "https://www.financialexpress.com/market/"},
)

SOURCE_TYPE_CONFIDENCE = {
    "official_filing": 0.95,
    "regulator": 0.93,
    "broker_api": 0.85,
    "publisher_rss": 0.75,
    "search_api": 0.65,
    "crawler": 0.6,
}
