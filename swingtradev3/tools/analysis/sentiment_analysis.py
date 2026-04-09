"""
Sentiment Analysis Tool
=======================
Multi-layer sentiment analysis:
  Layer 1: FinBERT (local, free) — pre-trained financial sentiment
  Layer 2: Keyword-based — detect specific catalysts
  Layer 3: LLM-based (optional) — deeper reasoning via NIM

Pure computation — no decisions, no agent logic.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from paths import CONTEXT_DIR
from storage import read_json, write_json


# FinBERT model loaded lazily
_FINBERT_PIPELINE = None


def _get_finbert():
    """Load FinBERT model — fails if unavailable, no fallback."""
    global _FINBERT_PIPELINE
    if _FINBERT_PIPELINE is None:
        from transformers import pipeline
        _FINBERT_PIPELINE = pipeline(
            "sentiment-analysis",
            model="ProsusAI/finbert",
            tokenizer="ProsusAI/finbert",
        )
    return _FINBERT_PIPELINE


# Catalyst keywords
CATALYST_KEYWORDS = {
    "earnings": ["earnings", "results", "profit", "revenue", "guidance", "beat", "miss", "quarterly"],
    "upgrade": ["upgrade", "raised", "target", "outperform", "buy", "overweight"],
    "downgrade": ["downgrade", "cut", "sell", "underperform", "reduce", "neutral"],
    "contract": ["contract", "deal", "order", "won", "award", "partnership", "tie-up"],
    "regulatory": ["sebi", "rbi", "regulatory", "ban", "penalty", "fine", "probe", "investigation"],
    "corporate_action": ["dividend", "split", "bonus", "rights", "buyback", "merger", "demerger"],
    "management": ["ceo", "resigned", "appointed", "board", "promoter", "insider"],
    "macro": ["inflation", "rate", "gdp", "budget", "policy", "fiscal", "monetary"],
}


class SentimentAnalyzer:
    """Multi-layer sentiment analysis for stock news."""

    def __init__(self, cache_path: Path | None = None, ttl_hours: int = 6) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "sentiment_cache.json")
        self.ttl_hours = ttl_hours

    def _cached(self, text_hash: str) -> dict[str, Any] | None:
        cache = read_json(self.cache_path, {})
        item = cache.get(text_hash)
        if not item:
            return None
        return item

    def _store(self, text_hash: str, result: dict[str, Any]) -> dict[str, Any]:
        cache = read_json(self.cache_path, {})
        cache[text_hash] = result
        write_json(self.cache_path, cache)
        return result

    def _hash_text(self, text: str) -> str:
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()

    def _finbert_sentiment(self, text: str) -> dict[str, Any]:
        """Layer 1: FinBERT sentiment analysis — no fallback."""
        pipeline = _get_finbert()
        truncated = text[:512]
        result = pipeline(truncated)[0]
        label = result["label"]
        confidence = result["score"]
        if label == "positive":
            score = confidence
        elif label == "negative":
            score = -confidence
        else:
            score = 0.0
        return {"score": round(score, 3), "label": label, "source": "finbert"}

    def _keyword_sentiment(self, text: str) -> dict[str, Any]:
        """Layer 2: Keyword-based catalyst detection."""
        text_lower = text.lower()
        catalysts = []
        positive_count = 0
        negative_count = 0

        for category, keywords in CATALYST_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    catalysts.append(category)
                    if category in ("earnings", "upgrade", "contract"):
                        positive_count += 1
                    elif category in ("downgrade", "regulatory"):
                        negative_count += 1
                    break  # One match per category is enough

        net = positive_count - negative_count
        if net > 0:
            score = min(net * 0.2, 1.0)
            label = "bullish"
        elif net < 0:
            score = max(net * 0.2, -1.0)
            label = "bearish"
        else:
            score = 0.0
            label = "neutral"

        return {
            "score": round(score, 3),
            "label": label,
            "catalysts": list(set(catalysts)),
            "source": "keyword",
        }

    def analyze_sentiment(self, text: str) -> dict[str, Any]:
        """
        Analyze sentiment of news text using multi-layer approach.

        Args:
            text: News article text or headline

        Returns:
            {sentiment_score, sentiment_label, catalysts, novelty, source_count}
        """
        text_hash = self._hash_text(text)
        cached = self._cached(text_hash)
        if cached is not None:
            return cached

        # Layer 1: FinBERT
        finbert_result = self._finbert_sentiment(text)

        # Layer 2: Keyword
        keyword_result = self._keyword_sentiment(text)

        # Combine: weighted average (FinBERT 60%, Keyword 40%)
        finbert_weight = 0.6 if finbert_result["source"] == "finbert" else 0.0
        keyword_weight = 1.0 - finbert_weight

        combined_score = (
            finbert_result["score"] * finbert_weight +
            keyword_result["score"] * keyword_weight
        )

        # Determine label
        if combined_score > 0.3:
            combined_label = "bullish"
        elif combined_score < -0.3:
            combined_label = "bearish"
        else:
            combined_label = "neutral"

        result = {
            "sentiment_score": round(combined_score, 3),
            "sentiment_label": combined_label,
            "catalyst_type": keyword_result.get("catalysts", []),
            "finbert_score": finbert_result["score"],
            "keyword_score": keyword_result["score"],
            "novelty": "unknown",  # Would need historical comparison
            "source_count": 1 + (1 if finbert_result["source"] == "finbert" else 0),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        return self._store(text_hash, result)

    def analyze_news_list(self, news_items: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze sentiment across multiple news items for a stock.

        Args:
            news_items: List of {title, content, url} dicts

        Returns:
            Aggregated sentiment across all news items
        """
        if not news_items:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "catalyst_type": [],
                "article_count": 0,
                "source": "no_news",
            }

        scores = []
        all_catalysts = set()
        bullish_count = 0
        bearish_count = 0

        for item in news_items:
            text = f"{item.get('title', '')} {item.get('content', '')}"
            if not text.strip():
                continue
            result = self.analyze_sentiment(text)
            scores.append(result["sentiment_score"])
            all_catalysts.update(result.get("catalyst_type", []))
            if result["sentiment_label"] == "bullish":
                bullish_count += 1
            elif result["sentiment_label"] == "bearish":
                bearish_count += 1

        avg_score = sum(scores) / len(scores) if scores else 0.0

        if avg_score > 0.2:
            label = "bullish"
        elif avg_score < -0.2:
            label = "bearish"
        else:
            label = "neutral"

        return {
            "sentiment_score": round(avg_score, 3),
            "sentiment_label": label,
            "catalyst_type": list(all_catalysts),
            "article_count": len(scores),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": len(scores) - bullish_count - bearish_count,
            "source": "aggregated",
            "analyzed_at": datetime.utcnow().isoformat(),
        }
