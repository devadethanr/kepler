from __future__ import annotations


PROJECTION_VERSION = "phase11.v1"
CURSOR_NAME = "execution_events"

GRAPH_LABELS = {
    "Stock",
    "Sector",
    "Index",
    "ResearchRun",
    "ResearchCandidate",
    "NewsArticle",
    "SignalSnapshot",
    "TechnicalSnapshot",
    "FundamentalSnapshot",
    "SentimentSnapshot",
    "RegimeSnapshot",
    "TradeMemory",
    "Observation",
    "Lesson",
    "FailurePattern",
    "SkillVersion",
    "ExecutionEvent",
    "OrderIntent",
    "Approval",
    "Position",
}

GRAPH_RELATIONSHIPS = {
    "MEMBER_OF",
    "BELONGS_TO_SECTOR",
    "ANALYZED_IN",
    "HAS_SIGNAL",
    "HAS_TECHNICAL",
    "HAS_FUNDAMENTAL",
    "HAS_SENTIMENT",
    "MENTIONS",
    "AFFECTS_STOCK",
    "UNDER_REGIME",
    "CANDIDATE_FOR",
    "GENERATED_SNAPSHOT",
    "GENERATED_INTENT",
    "EXECUTED_AS",
    "CLOSED_AS",
    "PRODUCED_OBSERVATION",
    "SUPPORTS_LESSON",
    "SIMILAR_TO",
    "FAILED_DURING",
    "ABOUT_STOCK",
    "APPLIES_TO_STOCK",
    "ORDER_INTENT_FOR",
    "APPROVAL_FOR",
    "POSITION_FOR",
}
