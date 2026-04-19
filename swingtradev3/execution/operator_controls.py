from __future__ import annotations

from datetime import datetime
from typing import Any

from memory.db import session_scope
from memory.repositories import MemoryRepository


WORKER_STATUS_KEY = "worker_status"
FAILED_EVENT_RETRY_PREFIX = "retry_failed_event:"
BLOCK_NEW_ENTRIES_KEY = "block_new_entries"
RECONCILIATION_STATUS_KEY = "reconciliation_status"


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


def _dispatch_block_alert(message: str, level: str) -> None:
    """Fire-and-forget Telegram alert on block transitions.

    Runs the async AlertsTool from sync code by scheduling on the active event
    loop (if any) or swallowing silently. Import is deferred so tests that patch
    the alerts pipeline keep working.
    """
    try:
        import asyncio as _asyncio

        from tools.execution.alerts import AlertsTool

        tool = AlertsTool()
        try:
            loop = _asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            loop.create_task(tool.send_alert(message, level=level))
        else:
            _asyncio.run(tool.send_alert(message, level=level))
    except Exception:
        # Alerts are best-effort; never block the kill-switch on alert failures.
        pass


def set_block_new_entries(
    *,
    reason: str,
    source: str,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add ``reason`` to the active-reason set. Block remains active while set is non-empty."""
    normalized_reason = str(reason or "unknown").strip() or "unknown"
    now = _now_iso()
    with session_scope() as session:
        repo = MemoryRepository(session)
        existing = repo.get_operator_control(BLOCK_NEW_ENTRIES_KEY)
        existing_value = dict((existing or {}).get("value", {}) or {})
        active_reasons = {
            str(item).strip()
            for item in existing_value.get("active_reasons", [])
            if str(item).strip()
        }
        was_blocked = bool(existing_value.get("blocked"))
        new_reason = normalized_reason not in active_reasons
        active_reasons.add(normalized_reason)

        history = list(existing_value.get("history", []))
        history.append(
            {
                "event": "set",
                "reason": normalized_reason,
                "source": source,
                "at": now,
                "detail": dict(detail or {}),
            }
        )
        history = history[-20:]  # bounded log

        value = {
            "blocked": True,
            "active_reasons": sorted(active_reasons),
            "latest_reason": normalized_reason,
            "latest_source": source,
            "latest_detail": dict(detail or {}),
            "set_at": existing_value.get("set_at") if was_blocked else now,
            "updated_at": now,
            "history": history,
        }
        result = repo.upsert_operator_control(
            control_key=BLOCK_NEW_ENTRIES_KEY,
            value=value,
            payload={"type": "kill_switch"},
            source=source,
        )

    if not was_blocked or new_reason:
        _dispatch_block_alert(
            f"⛔ New entries blocked: reason={normalized_reason} source={source}",
            level="critical",
        )
    return result


def clear_block_new_entries(
    *,
    source: str,
    reason: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Remove ``reason`` from the active-reason set (or clear all if ``reason is None``)."""
    now = _now_iso()
    with session_scope() as session:
        repo = MemoryRepository(session)
        existing = repo.get_operator_control(BLOCK_NEW_ENTRIES_KEY)
        existing_value = dict((existing or {}).get("value", {}) or {})
        was_blocked = bool(existing_value.get("blocked"))
        active_reasons = {
            str(item).strip()
            for item in existing_value.get("active_reasons", [])
            if str(item).strip()
        }

        if reason is None:
            cleared_reasons = sorted(active_reasons)
            active_reasons = set()
        else:
            normalized_reason = str(reason).strip()
            cleared_reasons = [normalized_reason] if normalized_reason in active_reasons else []
            active_reasons.discard(normalized_reason)

        still_blocked = bool(active_reasons)
        history = list(existing_value.get("history", []))
        history.append(
            {
                "event": "clear",
                "cleared_reasons": cleared_reasons,
                "source": source,
                "at": now,
                "detail": dict(detail or {}),
                "still_blocked": still_blocked,
                "remaining_reasons": sorted(active_reasons),
            }
        )
        history = history[-20:]

        value = {
            "blocked": still_blocked,
            "active_reasons": sorted(active_reasons),
            "latest_source": source,
            "latest_detail": dict(detail or {}),
            "cleared_at": None if still_blocked else now,
            "updated_at": now,
            "history": history,
        }
        if still_blocked and existing_value.get("latest_reason") in active_reasons:
            value["latest_reason"] = existing_value.get("latest_reason")
        elif still_blocked:
            value["latest_reason"] = next(iter(sorted(active_reasons)))
        result = repo.upsert_operator_control(
            control_key=BLOCK_NEW_ENTRIES_KEY,
            value=value,
            payload={"type": "kill_switch"},
            source=source,
        )

    if was_blocked and not still_blocked and cleared_reasons:
        _dispatch_block_alert(
            f"✅ Entries unblocked (cleared: {', '.join(cleared_reasons)}) source={source}",
            level="info",
        )
    return result


def read_block_new_entries() -> dict[str, Any] | None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        control = repo.get_operator_control(BLOCK_NEW_ENTRIES_KEY)
    if control is None:
        return None
    return dict(control.get("value", {}))


def is_block_new_entries_active() -> bool:
    record = read_block_new_entries()
    if record is None:
        return False
    return bool(record.get("blocked"))


def active_block_reasons() -> list[str]:
    record = read_block_new_entries() or {}
    return [str(item) for item in record.get("active_reasons", [])]


def write_reconciliation_status(payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    normalized = {**payload, "updated_at": _now_iso()}
    with session_scope() as session:
        repo = MemoryRepository(session)
        return repo.upsert_operator_control(
            control_key=RECONCILIATION_STATUS_KEY,
            value=normalized,
            payload={"owner": "reconciler"},
            source=source,
        )


def read_reconciliation_status() -> dict[str, Any] | None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        control = repo.get_operator_control(RECONCILIATION_STATUS_KEY)
    if control is None:
        return None
    return dict(control.get("value", {}))


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
