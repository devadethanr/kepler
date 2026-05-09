# News Aggregation And Crawler Architecture

Status: implemented for JSON/Postgres/dashboard news ingestion; Memgraph projection remains Phase 11  
Last reviewed: 2026-05-07  
Scope: Indian equity news, corporate disclosures, regulator/macro alerts, broker/platform news,
and unofficial crawler-based discovery.

## Purpose

The current news path is too narrow for live trading research. It mostly depends on Tavily/DDGS
search, which caused repeated low-quality or repeated stock news and weak coverage outside a few
large names.

This plan defines a multi-source news ingestion layer that:

- treats exchange and regulator sources as canonical
- uses Upstox News API as a core broker/news source
- adds publisher RSS and search feeds for context
- adds unofficial crawlers for maximum coverage
- normalizes all records into one schema for agents, Telegram, dashboard, Postgres, and future
  Memgraph `NewsArticle` memory
- keeps execution safety independent of crawler availability

Plain English rule:

```text
Official filings decide.
Broker/news APIs and publishers inform.
Unofficial crawlers discover and enrich.
Worker execution never depends on an unofficial crawler.
```

## Source Priority

Confidence order:

1. Exchange filings and exchange disclosure feeds
2. Regulator and macro feeds
3. Upstox News API
4. Official publisher RSS feeds
5. Publisher/company pages crawled directly
6. Broker/platform public pages and market aggregators
7. Social/news-flow discovery pages

When an unofficial item claims a price-sensitive event, the system should try to confirm it against
NSE, BSE, SEBI, RBI, company IR, or another high-confidence source before treating it as a strong
research signal.

## Official Core Sources

| Priority | Source | Access | Coverage | Integration |
|---:|---|---|---|---|
| 1 | NSE corporate announcements RSS | `https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml` | NSE listed-company announcements, near real-time | Primary filing feed; dedupe by title/link/pubDate and, where enriched, NSE sequence id |
| 2 | NSE category RSS feeds | `https://www.nseindia.com/rss-feed` | Financial results, corporate actions, board meetings, insider trading, SAST, shareholding, voting, circulars | Category-specific catalysts and event classification |
| 3 | NSE corporate announcements JSON | `https://www.nseindia.com/api/corporate-announcements?...` | Structured announcement fields, symbol, ISIN, attachment metadata | Optional enrichment/fallback after RSS; browser-session headers may be required |
| 4 | BSE corporate announcements | `https://www.bseindia.com/corporates/ann.html?anntype=D` and `https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w?...` | BSE listed-company disclosures with `NEWSID`, category, attachment, dissemination time | Core BSE feed; dedupe by `NEWSID` |
| 5 | BSE RSS page | `https://www.bseindia.com/rss-feed.html` | BSE RSS catalog where available | Prefer RSS over JSON if stable corporate-announcement XML URLs are found |
| 6 | SEBI RSS | `https://www.sebi.gov.in/rss.html`, `https://www.sebi.gov.in/sebirss.xml` | Circulars, orders, recovery, enforcement, press releases | Mandatory regulatory feed |
| 7 | RBI RSS | `https://www.rbi.org.in/Scripts/rss.aspx`, `https://rbi.org.in/pressreleases_rss.xml` | Press releases, notifications, rates, banking/NBFC/macroeconomic updates | Mandatory BFSI and macro risk feed |
| 8 | PIB RSS | `https://www.pib.gov.in/ViewRss.aspx?lang=1&reg=22` | Government policy, ministry releases, cabinet/sector updates | Low-priority macro/policy feed with keyword filters |
| 9 | Upstox News API | `https://upstox.com/developer/api-documentation/get-news/` | Stock/instrument news by `instrument_key`, positions, holdings, market context | Core broker/news source; requires Upstox account/app token |
| 10 | Zerodha Z-Connect RSS | `https://zerodha.com/z-connect/feed` | Broker/platform, market education, operational updates | Narrow broker/platform context; not stock-level news |

## Official Publisher And Search Sources

These are official public pages/RSS/search surfaces from publishers or data platforms. They are
context sources, not final proof for trade execution.

| Source | Access | Coverage | Notes |
|---|---|---|---|
| Moneycontrol RSS | `https://www.moneycontrol.com/features/rss/` | Markets, stocks, business, economy, IPOs | Good broad supplement; dedupe heavily |
| Economic Times RSS | `https://economictimes.indiatimes.com/rss.cms` | ETMarkets, stocks, companies, economy | Good for analyst calls, market context, recos |
| Livemint market pages/RSS-like pages | `https://www.livemint.com/market/stock-market-news` | Pre-market, stocks to watch, broker notes, earnings, IPOs | HTML crawl if RSS is incomplete |
| CNBC TV18 | `https://www.cnbctv18.com/market/stocks/` | Results, management quotes, order wins, market movers | Use static parser first, render fallback only when needed |
| NDTV Profit | `https://www.ndtvprofit.com/markets/stocks/` | Fast earnings and market headlines | Good editorial context |
| Business Standard | `https://www.business-standard.com/markets/news` | Markets, companies, IPOs, policy | Direct static fetch may be blocked; AMP/browser fallback useful |
| BusinessLine | `https://www.thehindubusinessline.com/markets/stock-markets/` | Industrials, commodities, policy, company actions | Useful for midcaps and sector policy |
| Financial Express | `https://www.financialexpress.com/market/` | IPOs, earnings, broker views, stocks to watch | Good enrichment source |
| GDELT DOC 2.0 | `https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/` | Global web news search and entity discovery | Search layer for company/topic discovery |
| Google News RSS | `https://news.google.com/rss/search?q=...&hl=en-IN&gl=IN&ceid=IN:en` | Cross-source headline search | Watchlist-only search; noisy but useful |

## Crawler Engine Plan

The crawler stack should be local-first and deterministic. AI is optional and should not be needed
for normal crawling.

Default chain:

```text
feedparser/httpx discovery
    -> deterministic source parser
    -> trafilatura article extraction
    -> Crawl4AI/Playwright JS fallback
    -> optional Firecrawl managed fallback
    -> normalized NewsItem
    -> optional LLM sentiment/entity/catalyst analysis
```

| Rank | Tool | Role | Decision |
|---:|---|---|---|
| 1 | `feedparser` + `httpx/aiohttp` | RSS and static HTTP discovery | Already fits the repo; default for feeds and static pages |
| 2 | `trafilatura` | Article text/metadata/Markdown extraction | Add as default article extractor |
| 3 | Crawl4AI | JS-heavy and LLM-ready page extraction | Add as the main open-source browser crawler |
| 4 | Playwright | Low-level browser fallback and network capture | Use through Crawl4AI or direct targeted adapters |
| 5 | Firecrawl managed API | Last-resort managed scrape/extract fallback | Keep optional behind `FIRECRAWL_API_KEY`; not default free path |
| 6 | Scrapy | Persistent crawler framework | Phase 2 only if many source-specific spiders are needed |
| 7 | Crawlee Python | Modern alternative to Scrapy with browser/proxy/session support | Phase 2 candidate; useful if Scrapy feels too heavy |
| 8 | Newspaper4k | News article parser fallback | Optional article-body fallback after trafilatura |
| 9 | Apache Nutch / Heritrix / Browsertrix | Web-scale or archival crawling | Do not use for this system; too heavy for curated trading news |

### Crawl4AI AI Usage

Crawl4AI does not require an AI model for normal crawling.

Use without AI for:

- fetching pages
- rendering JavaScript
- extracting Markdown
- running CSS/XPath extraction
- capturing links
- handling dynamic pages

Use AI optionally for:

- messy pages where stable selectors are not worth maintaining
- one-off structured extraction from unknown layouts
- fallback extraction into a defined schema

Kepler should keep crawling deterministic and reserve LLMs for post-extraction analysis:

- ticker/entity matching
- catalyst classification
- sentiment
- novelty detection
- short summaries for dashboard/Telegram

## Unofficial Crawl Targets

These sources maximize coverage. They should be treated as discovery/enrichment unless confirmed
by official sources.

| Priority | Target | URL Patterns | Extractable Fields | Engine |
|---:|---|---|---|---|
| 1 | Groww stock pages | `https://groww.in/stocks/<stock-slug>` | Embedded `newsData`, source, title, summary, URL, pubDate, corporate events, peers, symbol/ISIN | Static parser first; Crawl4AI fallback |
| 2 | Moneycontrol tag pages | `https://www.moneycontrol.com/news/tags/-<topic>.html` | JSON-LD `ItemList`, title, URL, rank, Last-Modified, topic news | Static parser |
| 3 | Moneycontrol company/market pages | `/india/stockpricequote/...`, `/markets/stock-deals/`, `/markets/earnings/` | Latest news, broker research, target price, deals, insider/deal activity, corporate actions, earnings calendar | Static parser plus Playwright for widgets |
| 4 | ETMarkets pages | `/markets/stocks/news`, `/markets/stocks/recos`, `/markets/stocks/mcalendar.cms`, `/<company>/stocksupdate/companyid-*.cms` | Stocks in news, analyst calls, target prices, results calendar, company-specific headlines | Static parser |
| 5 | Screener company pages | `https://www.screener.in/company/<SYMBOL>/` | Announcements, concalls, transcripts, PPTs, raw PDFs, credit ratings, filing summaries | Static parser; login-only features ignored |
| 6 | TradingView news flow/symbol news | `https://in.tradingview.com/news-flow/`, `/symbols/NSE-<SYMBOL>/news/` | Fast headline discovery, provider, timestamp, symbol links, corporate/economic filters | Crawl4AI/Playwright; discovery only |
| 7 | NDTV Profit market pages | `/markets`, `/markets/stocks/`, `/business/stocks`, `/markets/ipos` | Earnings, brokerage reaction, management commentary, market live items, IPOs | Static parser |
| 8 | CNBC TV18 market pages | `/market/stocks/`, `/market/`, `/live-updates/` | Results, order wins, management quotes, TV-driven movers | Static parser; browser fallback if needed |
| 9 | Business Standard | `/markets/news`, `/companies/news`, `/topic/<topic>`, `/amp/...` | Policy/regulatory stories, IPOs, earnings, sector news | AMP/static parser; Crawl4AI fallback |
| 10 | Livemint | `/market/stock-market-news`, `/market/`, `/topic/<topic>` | Stocks to watch, broker recos, IPOs, earnings, macro setup | Static parser |
| 11 | BusinessLine | `/markets/stock-markets/`, `/companies/`, `/economy/policy/`, `/markets/commodities/` | Order wins, industrials, commodities, policy, midcap actions | Static parser |
| 12 | Financial Express | `/market/`, `/about/<company>/`, IPO pages | IPOs, broker notes, results, market movers | Static parser |
| 13 | Trendlyne | `/equity/<id>/<SYMBOL>/...`, `/news-by-trendlyne/None/` | Filings summaries, watchlist announcements, forecast/sentiment pages | Crawl4AI/Playwright; enrichment only |
| 14 | Tickertape | `/stocks/<slug>-<code>` | Stock news/opinions, events, fundamentals snippets | Crawl4AI/Playwright; enrichment only |
| 15 | Tijori | `/company/<slug>` | Timeline, company updates, sector links, business change signals | Crawl4AI/Playwright; enrichment only |
| 16 | Company investor relations pages | Company-specific IR/news/press-release pages | Press releases, presentations, transcripts, investor updates | Source-specific static parser |

## Normalized Data Model

Every provider should emit the same shape before analysis:

```python
NewsItem = {
    "provider": "nse_rss | bse_announcements | upstox_news | groww_crawler | ...",
    "source_type": "official_filing | regulator | broker_api | publisher_rss | crawler",
    "source_id": "stable provider id where available",
    "source_url": "original URL",
    "canonical_url": "deduped canonical URL",
    "title": "headline/title",
    "summary": "short source summary or snippet",
    "content_text": "extracted article text when available",
    "content_markdown": "LLM-ready markdown when available",
    "published_at_utc": "UTC datetime",
    "published_at_ist": "IST datetime",
    "fetched_at_ist": "IST datetime",
    "tickers": ["RELIANCE"],
    "isins": ["INE002A01018"],
    "company_names": ["Reliance Industries"],
    "category": "earnings | order_win | regulation | macro | broker_note | ipo | unknown",
    "confidence": 0.0,
    "raw_hash": "sha256 hash of normalized raw payload",
}
```

Provider health should also be persisted:

```python
NewsProviderHealth = {
    "provider": "groww_crawler",
    "enabled": True,
    "last_success_at_ist": "...",
    "last_failure_at_ist": "...",
    "last_error": None,
    "items_seen": 0,
    "items_emitted": 0,
    "dedupe_drops": 0,
    "empty_extractions": 0,
    "latency_ms": 0,
}
```

## Scheduling

Use existing scheduler phases and IST throughout.

| Phase | Cadence | Sources |
|---|---|---|
| Overnight | Every 30-60 minutes | NSE/BSE latest, SEBI/RBI/PIB, GDELT/Google watchlist, Groww/Moneycontrol/ET watchlist pages |
| 06:00 digest | Once | All official feeds, Upstox, publisher RSS, prior overnight crawler items |
| Pre-market | 08:00-09:10 | Stocks to watch, earnings calendar, corporate actions, broker notes, watchlist crawlers |
| Market active | 15-30 minutes for holdings; 30-60 minutes for watchlist | Upstox, NSE/BSE, Groww `newsData`, Moneycontrol/ET, TradingView discovery |
| Post-market | 15:30-18:00 | Results, exchange filings, bulk/block deals, earnings calendar, official circulars |
| Wind-down | 21:00 | Final news scan, dedupe, source-health summary |

## Integration Plan

### Phase A: Core Providers

- Refactor `NewsAggregator` behind provider adapters.
- Implement NSE RSS, BSE announcements, SEBI RSS, RBI RSS, Upstox News API, Moneycontrol RSS,
  and ET RSS.
- Keep `search_news`, `sweep_market_news`, and `search_stock_news` public methods compatible.
- Add provider health output for dashboard and audit trail.

### Phase B: Local Crawler Layer

- Add `trafilatura` to dependencies.
- Add `CrawlerProvider` and source configs for Groww, Moneycontrol pages, ETMarkets, Screener,
  NDTV Profit, CNBC TV18, Business Standard AMP, Livemint, BusinessLine, and Financial Express.
- Add Crawl4AI as the browser fallback for Groww/TradingView/Trendlyne/Tickertape/Tijori and
  any JS-heavy page.
- Keep Firecrawl as an optional last fallback where `FIRECRAWL_API_KEY` is configured.

### Phase C: Storage And Memory

- Persist normalized news to Postgres when schema is available.
- Keep JSON cache as compatibility projection only.
- Project research-useful items into Phase 11 Memgraph as `NewsArticle` nodes with
  `MENTIONS` and `AFFECTS_STOCK` edges.
- Dashboard should expose source health, raw headlines, dedupe/audit metadata, and agent usage.

### Phase D: Agent Usage

- `FilterAgent` should use normalized ticker matches instead of only broad text search.
- Sentiment agents should consume extracted text/markdown plus official confirmation status.
- Slow Brain/Phase 13 agents should use official filings as evidence anchors and crawler items as
  supporting context.
- Telegram alerts should include source, timestamp IST, official/unofficial label, and dashboard
  audit link.

## Testing Plan

Unit tests:

- NSE RSS parser with category extraction
- BSE announcements parser with `NEWSID` dedupe
- SEBI/RBI RSS parser with regulator classification
- Upstox News parser with missing-token and valid-token fixture paths
- Groww `newsData` extraction from static HTML
- Moneycontrol JSON-LD `ItemList` parser
- Screener announcements/concall parser
- ETMarkets company news parser
- `trafilatura` article extraction fallback
- Crawl4AI fallback wrapper with mocked crawler result

Regression tests:

- RELIANCE-only spam does not dominate broad market sweep
- malformed pseudo-tickers are rejected
- stale headlines are filtered by IST/UTC-aware max age
- duplicate source URLs and duplicate titles are collapsed
- source failure does not block other providers
- empty crawler extraction is recorded in provider health
- Telegram alerts respect cooldown and source confidence

Integration tests:

- `search_stock_news("RELIANCE")` returns normalized items from multiple providers when fixtures
  are enabled
- overnight news sweep emits only new, ticker-relevant items
- dashboard provider-health endpoint reflects failures and successes
- future Memgraph projector can consume `NewsItem` without needing provider-specific payloads

Validation commands:

```bash
cd swingtradev3
make test-file file=tests/test_phase2_data_layer.py
make test-file file=tests/test_phase2_research_agents.py
make test
```

All tests must run through the `swingtradev3/Makefile` and Docker path.

## Risks And Guardrails

- Unofficial crawlers will break when page markup changes; parser fixtures and provider health are
  mandatory.
- JS/browser crawlers are expensive; only use Crawl4AI/Playwright when static extraction fails.
- Do not let crawler failures affect order placement, reconciliation, kill switches, or broker
  state.
- Store source URLs and hashes for auditability.
- Keep confidence and confirmation status visible in dashboard and Telegram output.
- Avoid full-article redistribution; store enough extracted text for internal analysis and always
  retain source attribution.

## Definition Of Done

- [x] Official feeds and Upstox News API produce normalized `NewsItem` records.
- [x] Groww, Moneycontrol, ETMarkets, Screener, TradingView, and publisher crawler targets are
  wired into the stock-news crawler path.
- [x] Moneycontrol, ETMarkets, NDTV Profit, CNBC TV18, Business Standard, Livemint, BusinessLine,
  and Financial Express are wired into the broad market crawler path.
- [x] Crawl4AI fallback is available and does not require an AI model for normal operation.
- [x] Source health and crawl audit trail are visible in the dashboard News panel.
- [x] `FilterAgent` and sentiment analysis consume normalized news, not raw Tavily/DDGS payloads.
- [x] RELIANCE/news spam regression is covered by normalized-ticker tests.
- [x] Full Docker `make test` passes.

## Implementation Notes

- Runtime storage is dual path: normalized news is written to `context/news_items.json` for
  compatibility and to Postgres `news_articles`/`news_provider_health` tables when the memory
  schema is available.
- The dashboard reads news through `GET /dashboard/news`, not route-level JSON storage.
- Telegram position-news alerts include source, official/publisher/crawler label, confidence, and
  IST timestamps where supplied.
- Upstox News is implemented but inactive until `UPSTOX_ACCESS_TOKEN` and either
  `UPSTOX_INSTRUMENT_KEYS_JSON` or per-symbol `UPSTOX_INSTRUMENT_KEY_<TICKER>` values are set.
- Phase 11 should project trusted `NewsItem` rows into Memgraph `NewsArticle` nodes with
  stock/entity edges.
