from __future__ import annotations

import json
from typing import Any

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.events import Event

from config import cfg
from paths import STRATEGY_DIR


class ScorerAgent(BaseAgent):
    """
    Final scoring + shortlisting agent.
    Runs sequentially after BatchScannerAgent completes.
    Uses LlmAgent internally to score each stock.
    """
    def __init__(self, name: str = "ScorerAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> Event:
        qualified_stocks = ctx.session.state.get("qualified_stocks", [])
        stock_data = ctx.session.state.get("stock_data", {})
        
        scored = []
        for stock_info in qualified_stocks:
            ticker = stock_info["ticker"]
            signals = stock_info.get("signals", {})
            analysis = stock_data.get(ticker, {})
            
            # Make sure we actually have data for this stock
            if not analysis:
                continue
                
            technical = analysis.get("technical", {})
            fundamentals = analysis.get("fundamentals", {})
            sentiment = analysis.get("sentiment", {})
            options = analysis.get("options", {})
            timesfm = analysis.get("timesfm", {})
            
            prompt = self._build_prompt(
                ticker, signals, technical, fundamentals, sentiment, options, timesfm
            )
            
            # Using LlmAgent directly here for the specific stock
            scorer_llm = LlmAgent(
                name=f"Scorer_{ticker}",
                model=cfg.llm.adk.research_model,
                instruction="You are an experienced swing trader analyzing Indian equities.",
                description="Scores a single stock based on its deep analysis data."
            )
            
            response_event = None
            async for event in scorer_llm.run_async(ctx, prompt):
                if event.is_final_response():
                    response_event = event
                    
            if response_event and response_event.content:
                parsed = self._parse_response(response_event.content)
                if parsed:
                    parsed["ticker"] = ticker
                    parsed["signals"] = signals
                    scored.append(parsed)

        # Sort by score descending
        scored.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Shortlist top N
        max_shortlist = cfg.research.max_shortlist
        min_score = cfg.research.min_score_threshold
        shortlist = [
            s for s in scored[:max_shortlist]
            if s.get("score", 0) >= min_score
        ]

        ctx.session.state["scan_results"] = scored
        ctx.session.state["shortlist"] = shortlist

        return Event(
            author=self.name,
            content={"scored_count": len(scored), "shortlist_count": len(shortlist), "shortlist": shortlist},
        )

    def _load_skill_md(self) -> str:
        skill_path = STRATEGY_DIR / "SKILL.md"
        if skill_path.exists():
            return skill_path.read_text()
        return ""

    def _build_prompt(
        self,
        ticker: str,
        signals: dict,
        technical: dict,
        fundamentals: dict,
        sentiment: dict,
        options: dict,
        timesfm: dict,
    ) -> str:
        """Build the scoring prompt with chain-of-thought structure."""
        return f"""You are an experienced swing trader analyzing {ticker}.

## Trading Philosophy
{self._load_skill_md()}

## Data for {ticker}

### Signals
- Priority signals: {signals}

### Technical Indicators
{json.dumps(technical, indent=2, default=str)}

### Fundamentals
{json.dumps(fundamentals, indent=2, default=str)}

### Sentiment
{json.dumps(sentiment, indent=2, default=str)}

### Options
{json.dumps(options, indent=2, default=str)}

### TimesFM Forecast
{json.dumps(timesfm, indent=2, default=str)}

## Instructions
Analyze this stock and respond in JSON format:

1. State the bull case (3 reasons)
2. State the bear case (3 reasons)
3. State the base case (most likely outcome)
4. Score 0-10 based on expected value
5. Provide entry zone, stop loss, target
6. Identify setup type (breakout, pullback, earnings_play, sector_rotation, skip)

Respond ONLY with valid JSON:
{{
    "bull_case": ["reason1", "reason2", "reason3"],
    "bear_case": ["reason1", "reason2", "reason3"],
    "base_case": "description",
    "score": 7.5,
    "setup_type": "pullback",
    "entry_zone": {{"low": 1000, "high": 1020}},
    "stop_price": 980,
    "target_price": 1100,
    "holding_days": 15,
    "reasoning": "concise explanation"
}}
"""

    def _parse_response(self, response: str) -> dict[str, Any] | None:
        """Parse LLM JSON response."""
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            
        # Try to extract from the first { to the last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end+1]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
