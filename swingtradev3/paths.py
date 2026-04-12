from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT
CONTEXT_DIR = PROJECT_ROOT / "context"
KNOWLEDGE_DIR = CONTEXT_DIR / "knowledge"
LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"
STRATEGY_DIR = PROJECT_ROOT / "strategy"
OLD_DIR = PROJECT_ROOT / "old"


def ensure_runtime_dirs() -> None:
    for path in [
        CONTEXT_DIR,
        CONTEXT_DIR / "auth",
        CONTEXT_DIR / "daily",
        CONTEXT_DIR / "research",
        KNOWLEDGE_DIR,
        KNOWLEDGE_DIR / "wiki" / "stocks",
        KNOWLEDGE_DIR / "wiki" / "sectors",
        KNOWLEDGE_DIR / "wiki" / "themes",
        KNOWLEDGE_DIR / "wiki" / "trade_journal",
        LOGS_DIR,
        REPORTS_DIR,
        STRATEGY_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
