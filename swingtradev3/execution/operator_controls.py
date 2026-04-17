from __future__ import annotations

from datetime import datetime
from typing import Any

from memory.db import session_scope
from memory.repositories import MemoryRepository


WORKER_STATUS_KEY = "worker_status"
FAILED_EVENT_RETRY_PREFIX = "retry_failed_event:"


def _now_iso() -> str:
    return datetime.now().isoformat()


def write_worker_status(status: dict[str, Any]) -> dict[str, Any]:
    normalized = {**status, "updated_at": _now_iso()}
    with session_scope() as session:
        repo = MemoryRepository(session)
        return repo.upsert_operator_control(
            control_key=WORKER_STATUS_KEY,
            value=normalized,
            payload={"owner": "worker"},
            source="worker",
        )


def read_worker_status() -> dict[str, Any] | None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        control = repo.get_operator_control(WORKER_STATUS_KEY)
    if control is None:
        return None
    return dict(control.get("value", {}))


def request_failed_event_retry(event_id: str) -> dict[str, Any]:
    control_key = f"{FAILED_EVENT_RETRY_PREFIX}{event_id}"
    payload = {
        "event_id": event_id,
        "status": "pending",
        "requested_at": _now_iso(),
    }
    with session_scope() as session:
        repo = MemoryRepository(session)
        return repo.upsert_operator_control(
            control_key=control_key,
            value=payload,
            payload={"type": "failed_event_retry"},
            source="api",
        )


def list_pending_failed_event_retries() -> list[dict[str, Any]]:
    with session_scope() as session:
        repo = MemoryRepository(session)
        controls = repo.list_operator_controls(prefix=FAILED_EVENT_RETRY_PREFIX)
    return [control for control in controls if control.get("value", {}).get("status") == "pending"]


def mark_failed_event_retry(control_key: str, *, status: str, detail: str | None = None) -> dict[str, Any]:
    with session_scope() as session:
        repo = MemoryRepository(session)
        existing = repo.get_operator_control(control_key)
        value = dict(existing.get("value", {}) if existing else {})
        value["status"] = status
        value["updated_at"] = _now_iso()
        if detail:
            value["detail"] = detail
        return repo.upsert_operator_control(
            control_key=control_key,
            value=value,
            payload={"type": "failed_event_retry"},
            source="worker",
        )
