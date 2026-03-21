# research_program.md — Research Procedure v1.0

## Step 1 — Quick filter
Discard any ticker that fails the configured market-cap, volume, promoter-pledge, or 200 EMA checks.

## Step 2 — Data fetch
Collect market data, fundamentals, news, FII/DII flows, and options data when available.

## Step 3 — Analysis
Evaluate the stock through SKILL.md and return structured JSON with score, setup type, entry zone,
stop, target, expected hold, thesis reasoning, and risk flags.

## Step 4 — Shortlisting rules
- Keep score >= configured minimum
- Cap shortlist length by configured maximum
- Respect remaining portfolio capacity
- Respect sector concentration limit

## Step 5 — Output
- Write one research artifact per stock
- Write pending approvals for the morning briefing
- Send Telegram briefing with YES or NO approvals
