# Historical Upgrade Blueprint

> Historical ideation document. Many items below were later implemented, renamed, or superseded.
> For current system behavior and backlog, use:
> `docs/architecture/v2_adk_fastapi_design.md`,
> `docs/architecture/implementation_plan+extended.md`,
> `docs/progress/current-task.md`, and
> `docs/progress/todo+extended.md`.

## Making swingtradev3 a World-Class AI Swing Trader

> This document is the comprehensive upgrade blueprint. It details every enhancement needed to transform the current skeleton into a genuinely competitive, institutional-grade AI swing trading system.

---

## What Makes a Great Human Swing Trader?

An experienced swing trader doesn't just look at charts. They layer intelligence:

1. **Market regime awareness** — Is this a bull, bear, or choppy market? They adjust position sizing and aggressiveness accordingly
2. **Sector rotation intuition** — Money flows between sectors in cycles; they ride the wave, not fight it
3. **Catalyst timing** — Earnings, policy changes, contract wins, analyst upgrades — they know *when* to be in and when to stay out
4. **Risk-first thinking** — Every trade starts with "how much can I lose?" not "how much can I make?"
5. **Pattern recognition from experience** — "This looks like the 2019 IT sector rally" or "This is a bull trap, I've seen this before"
6. **Sentiment reading** — They read news, analyst calls, management commentary, and social chatter to gauge market mood
7. **Volume-price relationship mastery** — Smart money leaves footprints in volume
8. **Patience and discipline** — They wait for A+ setups and skip the rest

---

## 1. Market Regime Detection (NEW MODULE)

**Why:** A setup that works in a bull market fails in a bear market. The system must know *what kind of market it is* before scoring any stock.

**What to add:**
- `data/market_regime.py` — Classifies market state using:
  - Nifty 50 trend (above/below 200 EMA, ADX strength)
  - India VIX level (low = complacent bull, high = fear)
  - Breadth indicators (advance/decline ratio, new 52w highs vs lows)
  - FII/DII flow direction (accumulating or distributing?)
  - Market momentum (Nifty ROC 20d, 50d)
- Output: `{regime: "bull" | "bear" | "choppy" | "transition", confidence: 0-1, volatility_state: "low" | "normal" | "high"}`
- **Impact:** In bear regime → raise min_score threshold from 7.0 to 8.0, reduce position sizing by 50%, tighten stops
- **Packages:** Already have pandas-ta, TA-Lib — just need to implement the logic

---

## 2. Multi-Timeframe Analysis (ENHANCEMENT)

**Why:** Great traders don't just look at daily charts. They check weekly for the big picture and intraday for entry timing.

**What to add:**
- Weekly timeframe analysis (already partially exists in `kite_fetcher.py`)
- Monthly trend confirmation — is the monthly candle bullish?
- Entry timing: 15-min or 1-hour chart for precise entry within the daily setup
- **Implementation:** Extend `data/indicators/` to accept timeframe parameter, run indicators on weekly + monthly candles too

---

## 3. Institutional Flow Tracking (NEW MODULE)

**Why:** Smart money (FIIs, DIIs, mutual funds) moves markets. Following their footprints is one of the highest-edge signals in Indian markets.

**What to add:**
- `data/institutional_flows.py` — Track:
  - Daily FII/DII net flows (already partially in `tools/fii_dii_data.py`)
  - FII index futures long/short ratio (NSE publishes this daily)
  - FII index options PCR (put-call ratio for index = sentiment)
  - Block deals / bulk deals (NSE publishes daily — shows institutional interest in specific stocks)
  - Mutual fund monthly inflows/outflows by sector
  - Delivery percentage in cash market (high delivery % = accumulation)
- **Data sources:** NSE India website (free), Moneycontrol, Screener.in
- **Packages:** `requests` + `BeautifulSoup` for scraping, already have these

---

## 4. News Sentiment Engine (MAJOR UPGRADE)

**Why:** Currently you just fetch news articles. A great trader *reads between the lines* — is the sentiment positive, negative, or neutral? Is this new information or rehashed old news?

**What to add:**
- `tools/sentiment_analysis.py` — Multi-layer sentiment:
  - **Layer 1:** FinBERT (Hugging Face) — pre-trained financial sentiment model, runs locally, free
  - **Layer 2:** LLM-based sentiment via NIM — deeper reasoning on complex news
  - **Layer 3:** Keyword-based — detect specific catalysts (earnings beat, upgrade, contract win, regulatory action)
- `data/news_aggregator.py` — Aggregate from MORE sources:
  - Tavily (already have)
  - Google News RSS (free, no API key)
  - Moneycontrol RSS feeds (free)
  - Economic Times RSS (free)
  - Twitter/X API for social sentiment (optional, paid)
  - Reddit r/IndianStreetBets (free, via PRAW)
- **Output per stock:** `{sentiment_score: -1 to +1, sentiment_label: "bullish" | "neutral" | "bearish", catalyst_type: "earnings" | "upgrade" | "contract" | "regulatory" | "macro", novelty: "new" | "rehashed", source_count: N}`

**Key packages to add:**
- `transformers` + `ProsusAI/finbert` — Local financial sentiment, no API cost
- `praw` — Reddit API for social sentiment
- `feedparser` — RSS feed parsing
- `textblob` or `vaderSentiment` — Lightweight sentiment as fallback

---

## 5. Earnings & Events Intelligence (ENHANCEMENT)

**Why:** Currently you just check earnings dates. A great trader analyzes *earnings quality* — was the beat on revenue or just cost-cutting? What did management say in the concall?

**What to add:**
- `data/earnings_analyzer.py`:
  - Historical earnings surprise pattern (does this stock typically beat or miss?)
  - Revenue growth trajectory (accelerating or decelerating?)
  - Margin trend (expanding or contracting?)
  - Management commentary sentiment from concall transcripts
  - Analyst estimate revisions (upgrades/downgrades in last 30 days)
- `data/events_calendar.py`:
  - RBI policy dates (affects banking, real estate, auto)
  - Budget dates
  - F&O expiry dates (already tracked)
  - Index rebalancing dates (Nifty reshuffles create forced flows)
  - Lock-in expiry dates (IPOs — huge supply hits market)

**Data sources:**
- Screener.in for historical earnings data
- Trendlyne for estimate revisions (has free tier)
- NSE for RBI policy calendar
- `yfinance` for analyst estimates

---

## 6. Options Market Intelligence (ENHANCEMENT)

**Why:** Options market often leads the equity market. Smart money uses options to position before moves.

**What to add:**
- `data/options_analyzer.py`:
  - Stock-level PCR (put-call ratio) — >1 = bullish, <1 = bearish
  - Change in OI (open interest) — are writers covering or adding?
  - Max pain level — where option writers want price to expire
  - IV rank / IV percentile — is options expensive or cheap? (high IV = expected move)
  - Unusual options activity — large block trades in OTM options = smart money positioning
  - India VIX trend — rising VIX = fear, falling VIX = complacency
- **Data source:** NSE India options chain (free, scrapable)

---

## 7. Relative Strength Matrix (ENHANCEMENT)

**Why:** Currently you compare vs Nifty 50. A great trader compares vs *everything* — sector, index, peers, and momentum ranking across the entire universe.

**What to add:**
- `data/relative_strength.py` enhancements:
  - RS vs Nifty 200 (not just Nifty 50)
  - RS vs sector index (Nifty Bank, Nifty IT, etc.)
  - RS vs direct peers (top 5 competitors by market cap)
  - RS momentum — is RS improving or deteriorating? (rate of change of RS)
  - RS rank across entire Nifty 200 (1-200 ranking)
  - Minervini-style RS rating (percentage of stocks this one outperforms)

---

## 8. Volume-Price Analysis Engine (ENHANCEMENT)

**Why:** Volume tells you if smart money is behind a move. Price without volume is noise.

**What to add:**
- `data/indicators/volume.py` enhancements:
  - VWAP (Volume Weighted Average Price) — even for swing, weekly VWAP matters
  - Accumulation/Distribution line
  - Chaikin Money Flow (CMF)
  - Volume profile — where is the most volume traded? (support/resistance from volume nodes)
  - On-balance volume divergence (price making new highs but OBV not = distribution)
  - Delivery volume % (NSE publishes — high delivery = genuine buying, not intraday speculation)

---

## 9. Correlation & Portfolio Risk (NEW MODULE)

**Why:** Having 3 positions that are 80% correlated is not diversification — it's one big bet.

**What to add:**
- `risk/correlation_checker.py`:
  - Calculate pairwise correlation between all open positions (60-day rolling)
  - Alert if correlation > 0.7 between any two positions
  - Portfolio beta vs Nifty 50
  - Portfolio VaR (Value at Risk) — worst-case daily loss at 95% confidence
  - Expected portfolio return distribution
- **Impact:** Reject setups that increase portfolio correlation beyond threshold

---

## 10. Trade Review & Learning Loop (CRITICAL MISSING PIECE)

**Why:** This is what separates good traders from great ones — they learn from every trade.

**What to add (you have the modules, need to wire them):**
- `learning/trade_reviewer.py` — On every trade close:
  - Did the thesis play out? (compare NIM's reasoning to actual outcome)
  - Was the entry well-timed? (could it have been entered cheaper?)
  - Did the stop-loss work? (was it too tight, too loose, or just right?)
  - What was the max favorable excursion vs max adverse excursion?
  - Tag each trade with setup type, regime, sector, catalyst type
- `learning/stats_engine.py` — Monthly:
  - Win rate by setup type (breakouts vs pullbacks vs earnings plays)
  - Win rate by market regime (bull vs bear vs choppy)
  - Win rate by sector
  - Win rate by sentiment score at entry
  - Average winner/loser by holding period
  - Best and worst performing SKILL.md versions
  - Kelly-optimal position sizing
- `learning/lesson_generator.py` — Monthly:
  - NIM reviews all trades + observations
  - Proposes specific SKILL.md edits with evidence
  - "Breakout trades in bear regime lost 73% of the time — add regime filter"
  - "Stocks with sentiment score >0.5 and RS rank <20 won 82% — prioritize these"

---

## 11. Macro Intelligence Layer (NEW MODULE)

**Why:** Macro drives sector rotation. A great trader knows when RBI is about to cut rates (banks up, IT down) or when crude is spiking (paints, tyres down).

**What to add:**
- `data/macro_indicators.py`:
  - Crude oil price trend (affects: paints, tyres, OMCs, chemicals)
  - USD/INR trend (affects: IT, pharma = positive; importers = negative)
  - US 10Y yield trend (affects: rate-sensitive sectors)
  - India GDP growth trajectory
  - CPI inflation trend
  - RBI repo rate trajectory
  - Global market correlation (S&P 500, Nasdaq, Hang Seng)
- **Data sources:** FRED API (free), RBI website, Yahoo Finance

---

## 12. Smart Entry Timing (ENHANCEMENT)

**Why:** Even a great setup can be entered poorly. A great trader waits for the right moment within the day.

**What to add:**
- `tools/entry_timer.py`:
  - Don't buy at market open (9:15-9:30 is noise)
  - Wait for first 30-min candle to establish direction
  - Buy on pullback to VWAP or first support level
  - Avoid last 30 minutes (square-off volatility)
  - Check if today is F&O expiry (avoid entries)
  - Check if stock is in F&O ban (avoid entries)

---

## 13. Exit Intelligence (ENHANCEMENT)

**Why:** Great traders know *when to take profits* and *when to cut losses fast*.

**What to add:**
- `tools/exit_intelligence.py`:
  - Time-based exit: if stock hasn't moved in 5 days, thesis may be wrong — tighten stop
  - Momentum decay detection: if MACD histogram is shrinking while price rises = divergence = exit signal
  - Volume drying up on up days = lack of conviction = consider exit
  - Parabolic move detection: if stock moves 15%+ in 3 days = likely exhaustion = book partial profits
  - Sector rotation exit: if money is leaving the sector, exit even if individual stock looks okay

---

## 14. Alternative Data Sources (ADVANCED)

**Why:** Edge comes from information others don't have or don't process.

**What to add:**
- **Google Trends** — Search volume for stock name, product names (free via `pytrends`)
- **Job postings** — Companies hiring aggressively = growth signal (LinkedIn, Naukri scraping)
- **App downloads / web traffic** — For consumer tech companies (SensorTower, SimilarWeb APIs)
- **Social media sentiment** — Twitter/X, Reddit r/IndianStreetBets, StockTwits
- **Insider trading** — Promoter/director buys/sells (NSE publishes, BSE publishes)
- **Shareholding pattern changes** — Quarterly but very powerful

---

## 15. LLM Reasoning Upgrade (CRITICAL)

**Why:** Currently the LLM gets data and returns a score. A great trader *reasons through multiple scenarios*.

**What to add:**
- **Chain-of-thought prompting** — Before scoring, NIM must:
  1. State the bull case (3 reasons)
  2. State the bear case (3 reasons)
  3. State the base case (most likely outcome)
  4. Assign probabilities to each scenario
  5. THEN score based on expected value
- **Few-shot examples** — Include 3-5 historical examples of similar setups in the prompt ("This looks like RELIANCE in March 2024 which went up 15% in 10 days")
- **Self-consistency** — Run the same analysis 3 times with different temperatures, take the consensus
- **Counterfactual reasoning** — "What would need to happen for this trade to fail?" — if the answer is "almost anything," skip the trade
- **Confidence calibration** — Track if NIM's confidence scores match actual outcomes. If it says 8.5/10 but those trades only win 55% of the time, recalibrate.

---

## Recommended Package Additions

| Package | Purpose | Cost |
|---------|---------|------|
| `transformers` + `ProsusAI/finbert` | Financial sentiment analysis (local) | Free |
| `feedparser` | RSS feed parsing for news | Free |
| `praw` | Reddit API for social sentiment | Free |
| `pytrends` | Google Trends data | Free |
| `fredapi` | FRED macro data (US rates, GDP) | Free |
| `scipy` | Statistical tests, correlation analysis | Free |
| `scikit-learn` | ML models for regime detection | Free |
| `ta` | Additional technical indicators | Free |
| `empyrical` | Risk metrics (already via quantstats) | Free |
| `ccxt` | Crypto correlation (optional) | Free |
| `yfinance` | Already have — enhance usage | Free |

---

## Priority Order for Implementation

### Phase 1 — High Impact, Low Effort (do first):
1. Market regime detection
2. Sentiment analysis (FinBERT)
3. Multi-timeframe analysis
4. Entry timing logic
5. Wire up learning loop (already exists)

### Phase 2 — High Impact, Medium Effort:
6. Institutional flow tracking
7. Options market intelligence
8. Enhanced relative strength matrix
9. Volume-price analysis upgrades
10. LLM chain-of-thought reasoning

### Phase 3 — Medium Impact, Medium Effort:
11. Earnings & events intelligence
12. Correlation & portfolio risk
13. Exit intelligence
14. Macro indicators layer

### Phase 4 — Advanced, Differentiating:
15. Alternative data sources
16. Self-consistency LLM analysis
17. Confidence calibration system

---

## The Vision

What we're building is not just a technical analysis bot. It's an **AI-powered institutional-grade swing trading system** that:

1. **Sees the whole market** — regime, flows, sentiment, options, macro
2. **Thinks like a trader** — bull case, bear case, probabilities, expected value
3. **Learns from experience** — every trade improves SKILL.md
4. **Manages risk first** — correlation, VaR, regime-adjusted sizing
5. **Times entries and exits** — not just "what" but "when"
6. **Uses alternative data** — Google Trends, social sentiment, insider activity

The edge doesn't come from one thing — it comes from the **combination** of all these layers working together, with the LLM reasoning on top of structured data from every dimension.

---

## Current State vs Target State

| Dimension | Current State | Target State |
|-----------|--------------|-------------|
| **Market awareness** | None — treats all market conditions the same | Regime-aware — adjusts strategy to bull/bear/choppy |
| **Data sources** | Kite OHLCV + Tavily news + yfinance fundamentals | Kite + NSE options + FII/DII + RSS feeds + Reddit + Google Trends + macro + insider data |
| **Sentiment** | Raw news text passed to LLM | FinBERT + LLM + keyword detection = structured sentiment score |
| **Analysis depth** | Daily timeframe only | Daily + weekly + monthly + intraday entry timing |
| **LLM reasoning** | Single pass → score | Chain-of-thought → bull/bear/base cases → probabilities → expected value score |
| **Learning** | Modules exist, not wired | Full loop: trade review → stats → lesson → SKILL.md update → git commit |
| **Risk management** | Per-trade risk limits | Portfolio-level: correlation, VaR, regime-adjusted sizing |
| **Entry timing** | Anytime during market hours | Smart timing: avoid open/close, wait for VWAP pullback, check F&O ban |
| **Exit intelligence** | Fixed stop/target GTT only | Dynamic: time-based, momentum decay, volume drying, parabolic detection |
| **Options data** | Tool exists, not analyzed | PCR, OI changes, max pain, IV rank, unusual activity |
| **Relative strength** | vs Nifty 50 only | vs Nifty 200, sector, peers, with momentum and ranking |
| **Macro awareness** | None | Crude, USD/INR, US yields, RBI rates, global indices |

---

## Architecture After Upgrades

```
swingtradev3/
├── data/
│   ├── market_regime.py              [NEW] Market state classification
│   ├── institutional_flows.py        [NEW] FII/DII/block deals tracking
│   ├── news_aggregator.py            [NEW] Multi-source news collection
│   ├── earnings_analyzer.py          [NEW] Earnings quality analysis
│   ├── events_calendar.py            [NEW] RBI, budget, rebalancing dates
│   ├── options_analyzer.py           [NEW] Options chain intelligence
│   ├── macro_indicators.py           [NEW] Macro data layer
│   ├── kite_fetcher.py               [ENHANCED] Multi-timeframe support
│   ├── corporate_actions.py          [EXISTING]
│   ├── nifty200_loader.py            [EXISTING]
│   ├── universe_updater.py           [EXISTING]
│   └── indicators/
│       ├── momentum.py               [EXISTING]
│       ├── trend.py                  [EXISTING]
│       ├── volatility.py             [EXISTING]
│       ├── volume.py                 [ENHANCED] VWAP, CMF, volume profile
│       ├── structure.py              [EXISTING]
│       ├── relative_strength.py      [ENHANCED] Multi-benchmark RS
│       └── patterns.py              [EXISTING]
│
├── tools/
│   ├── market/
│   │   ├── market_data.py            [EXISTING]
│   │   ├── fundamental_data.py       [EXISTING]
│   │   ├── news_search.py            [EXISTING]
│   │   ├── fii_dii_data.py           [EXISTING]
│   │   └── options_data.py           [EXISTING]
│   ├── execution/
│   │   ├── order_execution.py        [EXISTING]
│   │   ├── gtt_manager.py            [EXISTING]
│   │   ├── risk_check.py             [EXISTING]
│   │   └── alerts.py                 [EXISTING]
│   ├── sentiment_analysis.py         [NEW] Multi-layer sentiment engine
│   ├── entry_timer.py                [NEW] Smart entry timing
│   └── exit_intelligence.py          [NEW] Dynamic exit logic
│
├── risk/
│   ├── engine.py                     [EXISTING]
│   ├── position_sizer.py             [EXISTING]
│   ├── circuit_breakers.py           [EXISTING]
│   ├── circuit_limit_checker.py      [EXISTING]
│   └── correlation_checker.py        [NEW] Portfolio correlation + VaR
│
├── learning/
│   ├── trade_reviewer.py             [EXISTING - wire to scheduler]
│   ├── stats_engine.py               [EXISTING - wire to scheduler]
│   ├── lesson_generator.py           [EXISTING - wire to scheduler]
│   └── skill_updater.py              [EXISTING - wire to scheduler]
│
├── llm/
│   ├── nim_client.py                 [ENHANCED] Chain-of-thought support
│   ├── router.py                     [EXISTING]
│   ├── tool_executor.py              [ENHANCED] Self-consistency mode
│   ├── prompt_builder.py             [ENHANCED] Few-shot examples
│   └── schemas/                      [NEW] JSON schemas for all tools
│
└── agents/
    ├── research_agent.py             [ENHANCED] Regime-aware scoring
    ├── execution_agent.py            [ENHANCED] Smart entry/exit
    └── reconciler.py                 [EXISTING]
```

---

*Created: April 4, 2026*
