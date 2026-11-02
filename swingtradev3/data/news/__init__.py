from __future__ import annotations

from data.news.parsers import (
    clean_text,
    extract_tickers_from_text,
    infer_category,
    parse_article_links,
    parse_bse_announcements,
    parse_epoch_ms,
    parse_groww_newsdata,
    parse_json_ld_item_list,
    parse_source_specific_html,
    parse_upstox_news,
)

__all__ = [
    "NewsAggregator",
    "clean_text",
    "extract_tickers_from_text",
    "infer_category",
    "parse_article_links",
    "parse_bse_announcements",
    "parse_epoch_ms",
    "parse_groww_newsdata",
    "parse_json_ld_item_list",
    "parse_source_specific_html",
    "parse_upstox_news",
]


def __getattr__(name: str):
    if name == "NewsAggregator":
        from data.news.aggregator import NewsAggregator

        return NewsAggregator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
