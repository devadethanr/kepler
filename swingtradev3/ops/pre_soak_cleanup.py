from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text

from config import cfg
from context_graph.projector import GraphProjector
from context_graph.repository import ContextGraphRepository
from memory import models as memory_models
from memory.db import get_engine, session_scope
from memory.repository import MemoryRepository
from paths import CONTEXT_DIR
from storage import write_json


CONFIRMATION = "RESET-PRE-SOAK"

RESET_TABLES = (
    "approvals",
    "broker_fills",
    "broker_orders",
    "cognition_reports",
    "cognition_runs",
    "entry_intents",
    "execution_events",
    "failure_incidents",
    "operator_controls",
    "order_intents",
    "positions",
    "protective_triggers",
    "reconciliation_runs",
    "scan_runs",
    "session_execution_plans",
    "trades",
)

PRESERVED_TABLES = (
    "account_state",
    "auth_sessions",
    "news_articles",
    "news_provider_health",
    "policy_overlays",
)


def _table_counts(tables: tuple[str, ...]) -> dict[str, int]:
    with get_engine().connect() as connection:
        return {
            table: int(connection.scalar(text(f'SELECT count(*) FROM "{table}"')) or 0)
            for table in tables
        }


def _refuse_unsafe_reset() -> None:
    if cfg.trading.mode.value == "live":
        raise RuntimeError("pre-soak cleanup is disabled in live mode")

    with session_scope() as session:
        trade_count = int(
            session.scalar(select(func.count()).select_from(memory_models.TradeRow)) or 0
        )
        position_count = int(
            session.scalar(select(func.count()).select_from(memory_models.PositionRow)) or 0
        )
    if trade_count or position_count:
        raise RuntimeError(
            "pre-soak cleanup refuses to remove trading history: "
            f"trades={trade_count}, positions={position_count}"
        )


def _reset_postgres() -> None:
    table_list = ", ".join(f'"{table}"' for table in RESET_TABLES)
    with get_engine().begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY"))

    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_operator_control(
            control_key="trading_enabled",
            value={"enabled": True, "latest_source": "pre_soak_cleanup", "history": []},
            payload={"type": "operator_flag"},
            source="pre_soak_cleanup",
            record_event=False,
        )
        repo.upsert_operator_control(
            control_key="new_entries_enabled",
            value={"enabled": True, "latest_source": "pre_soak_cleanup", "history": []},
            payload={"type": "operator_flag"},
            source="pre_soak_cleanup",
            record_event=False,
        )
        repo.upsert_operator_control(
            control_key="exit_only_mode",
            value={"enabled": False, "latest_source": "pre_soak_cleanup", "history": []},
            payload={"type": "operator_flag"},
            source="pre_soak_cleanup",
            record_event=False,
        )
        repo.upsert_operator_control(
            control_key="block_new_entries",
            value={
                "blocked": False,
                "active_reasons": [],
                "latest_source": "pre_soak_cleanup",
                "history": [],
            },
            payload={"type": "kill_switch"},
            source="pre_soak_cleanup",
            record_event=False,
        )


def _reset_runtime_files() -> None:
    def write_projection(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    write_projection(CONTEXT_DIR / "trades.json", [])
    write_projection(CONTEXT_DIR / "pending_approvals.json", [])
    write_json(CONTEXT_DIR / "failed_events.json", [])
    write_json(CONTEXT_DIR / "agent_activity.json", {"agents": {}, "last_updated": None})
    write_json(CONTEXT_DIR / "scan_status.json", {"status": "idle"})
    (CONTEXT_DIR / "event_log.jsonl").write_text("", encoding="utf-8")

    state_path = CONTEXT_DIR / "state.json"
    if state_path.exists():
        with session_scope() as session:
            account = MemoryRepository(session).get_account_state_payload()
        if account:
            write_projection(state_path, account)


def _news_payload(row: memory_models.NewsArticleRow) -> dict[str, Any]:
    payload = dict(row.payload or {})
    return {
        **payload,
        "news_id": row.news_id,
        "provider": row.provider,
        "source_type": row.source_type,
        "title": row.title,
        "canonical_url": row.canonical_url,
        "category": row.category,
        "confidence": row.confidence,
        "tickers": list(row.tickers or []),
        "published_at": row.published_at.isoformat() if row.published_at else None,
    }


def _rebuild_context_graph() -> dict[str, int]:
    graph = ContextGraphRepository()
    try:
        graph._run("MATCH (n) DETACH DELETE n")
        graph.ensure_schema()
        static_counts = GraphProjector(graph_repo=graph).seed_static_context()

        with session_scope() as session:
            news_rows = session.scalars(
                select(memory_models.NewsArticleRow).order_by(
                    memory_models.NewsArticleRow.published_at.asc().nullsfirst()
                )
            ).all()
            news_items = [_news_payload(row) for row in news_rows]

        for offset in range(0, len(news_items), 100):
            graph.upsert_news_items(
                news_items[offset : offset + 100],
                source="postgres_news_restore",
            )
        graph.set_projection_cursor(0)
        return {**static_counts, "news": len(news_items)}
    finally:
        graph.close()


def cleanup(*, apply: bool, confirmation: str | None) -> dict[str, Any]:
    _refuse_unsafe_reset()
    before = _table_counts(RESET_TABLES + PRESERVED_TABLES)
    if not apply:
        return {
            "status": "dry_run",
            "would_reset": {table: before[table] for table in RESET_TABLES},
            "would_preserve": {table: before[table] for table in PRESERVED_TABLES},
        }
    if confirmation != CONFIRMATION:
        raise RuntimeError(f"pass --confirm {CONFIRMATION} to apply the cleanup")

    _reset_postgres()
    _reset_runtime_files()
    graph_counts = _rebuild_context_graph()
    after = _table_counts(RESET_TABLES + PRESERVED_TABLES)
    return {
        "status": "completed",
        "reset": {table: {"before": before[table], "after": after[table]} for table in RESET_TABLES},
        "preserved": {table: after[table] for table in PRESERVED_TABLES},
        "context_graph": graph_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset contaminated pre-soak runtime state")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")
    args = parser.parse_args()
    result = cleanup(apply=args.apply, confirmation=args.confirm)
    for section, value in result.items():
        print(f"{section}: {value}")


if __name__ == "__main__":
    main()
