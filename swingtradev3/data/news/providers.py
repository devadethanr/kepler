from __future__ import annotations

from data.news.broker_providers import NewsBrokerProviderMixin
from data.news.crawler_providers import NewsCrawlerProviderMixin
from data.news.feed_providers import NewsFeedProviderMixin
from data.news.search_providers import NewsSearchProviderMixin


class NewsProviderMixin(
    NewsFeedProviderMixin,
    NewsSearchProviderMixin,
    NewsBrokerProviderMixin,
    NewsCrawlerProviderMixin,
):
    """Composed provider surface used by NewsAggregator."""
