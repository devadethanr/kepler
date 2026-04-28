from __future__ import annotations

from datetime import datetime
from typing import Any

from memory.db import session_scope
from memory.repositories import MemoryRepository


WORKER_STATUS_KEY = "worker_status"
FAILED_EVENT_RETRY_PREFIX = "retry_failed_event:"
RECONCILE_ACK_PREFIX = "reconcile_ack:"
BLOCK_NEW_ENTRIES_KEY = "block_new_entries"
RECONCILIATION_STATUS_KEY = "reconciliation_status"

# Phase 7: first-class operator control flags (orthogonal to block_new_entries).
TRADING_ENABLED_KEY = "trading_enabled"
NEW_ENTRIES_ENABLED_KEY = "new_entries_enabled"
EXIT_ONLY_MODE_KEY = "exit_only_mode"
FLATTEN_REQUEST_KEY = "flatten_requested"

_HISTORY_LIMIT = 20


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


def request_reconcile_ack(*, position_id: str, resolution: str, source: str) -> dict[str, Any]:
    normalized_position = str(position_id).strip().upper()
    control_key = f"{RECONCILE_ACK_PREFIX}{normalized_position}"
    payload = {
        "position_id": normalized_position,
        "resolution": str(resolution).strip(),
        "status": "pending",
        "requested_at": _now_iso(),
    }
    with session_scope() as session:
        repo = MemoryRepository(session)
        result = repo.upsert_operator_control(
            control_key=control_key,
            value=payload,
            payload={"type": "reconcile_ack"},
            source=source,
        )
        repo.append_execution_event(
            event_type="reconcile_ack_requested",
            entity_type="position",
            entity_id=normalized_position,
            source=source,
            payload={"resolution": payload["resolution"]},
        )
        return result


def list_pending_reconcile_acks() -> list[dict[str, Any]]:
    with session_scope() as session:
        repo = MemoryRepository(session)
        controls = repo.list_operator_controls(prefix=RECONCILE_ACK_PREFIX)
    return [control for control in controls if control.get("value", {}).get("status") == "pending"]


def mark_reconcile_ack(
    control_key: str,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    with session_scope() as session:
        repo = MemoryRepository(session)
        existing = repo.get_operator_control(control_key)
        value = dict(existing.get("value", {}) if existing else {})
        value["status"] = status
        value["updated_at"] = _now_iso()
        if detail:
            value["detail"] = detail
        if result is not None:
            value["result"] = dict(result)
        updated = repo.upsert_operator_control(
            control_key=control_key,
            value=value,
            payload={"type": "reconcile_ack"},
            source="worker",
        )
        repo.append_execution_event(
            event_type="reconcile_ack_processed",
            entity_type="operator_control",
            entity_id=control_key,
            source="worker",
            payload={"status": status, "detail": detail, "result": dict(result or {})},
        )
        return updated


def _dispatch_control_alert(message: str, level: str) -> None:
    """Fire-and-forget Telegram alert on operator-control transitions.

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


# Backwards-compatible alias. Phase 6 tests and callers use this name.
_dispatch_block_alert = _dispatch_control_alert


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
        _dispatch_control_alert(
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
        _dispatch_control_alert(
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


# ---------------------------------------------------------------------------
# Phase 7: boolean operator-control flags (trading_enabled, new_entries_enabled,
# exit_only_mode) + flatten_requested
# ---------------------------------------------------------------------------


def _set_bool_flag(
    *,
    control_key: str,
    enabled: bool,
    source: str,
    reason: str | None,
    default: bool,
    alert_on_disable: str,
    alert_on_enable: str,
) -> dict[str, Any]:
    now = _now_iso()
    with session_scope() as session:
        repo = MemoryRepository(session)
        existing = repo.get_operator_control(control_key)
        existing_value = dict((existing or {}).get("value", {}) or {})
        previous = bool(existing_value.get("enabled", default))
        history = list(existing_value.get("history", []))
        history.append(
            {
                "event": "set",
                "enabled": bool(enabled),
                "previous": previous,
                "source": source,
                "reason": reason,
                "at": now,
            }
        )
        history = history[-_HISTORY_LIMIT:]
        value = {
            "enabled": bool(enabled),
            "latest_source": source,
            "latest_reason": reason,
            "updated_at": now,
            "history": history,
        }
        result = repo.upsert_operator_control(
            control_key=control_key,
            value=value,
            payload={"type": "operator_flag"},
            source=source,
        )

    if previous != bool(enabled):
        if enabled:
            _dispatch_control_alert(alert_on_enable, level="info")
        else:
            _dispatch_control_alert(alert_on_disable, level="critical")
    return result


def _read_bool_flag(control_key: str, *, default: bool) -> bool:
    with session_scope() as session:
        repo = MemoryRepository(session)
        control = repo.get_operator_control(control_key)
    if control is None:
        return default
    value = dict(control.get("value") or {})
    return bool(value.get("enabled", default))


def _read_flag_record(control_key: str) -> dict[str, Any] | None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        control = repo.get_operator_control(control_key)
    if control is None:
        return None
    return dict(control.get("value") or {})


# trading_enabled — master on/off. Default True.
def set_trading_enabled(*, enabled: bool, source: str, reason: str | None = None) -> dict[str, Any]:
    return _set_bool_flag(
        control_key=TRADING_ENABLED_KEY,
        enabled=enabled,
        source=source,
        reason=reason,
        default=True,
        alert_on_disable=f"⛔ Trading disabled: reason={reason or 'unspecified'} source={source}",
        alert_on_enable=f"✅ Trading re-enabled: source={source}",
    )


def is_trading_enabled() -> bool:
    return _read_bool_flag(TRADING_ENABLED_KEY, default=True)


def read_trading_enabled() -> dict[str, Any] | None:
    return _read_flag_record(TRADING_ENABLED_KEY)


# new_entries_enabled — operator-owned hard-off for new entries. Default True.
def set_new_entries_enabled(*, enabled: bool, source: str, reason: str | None = None) -> dict[str, Any]:
    return _set_bool_flag(
        control_key=NEW_ENTRIES_ENABLED_KEY,
        enabled=enabled,
        source=source,
        reason=reason,
        default=True,
        alert_on_disable=f"⛔ New entries disabled by operator: reason={reason or 'unspecified'} source={source}",
        alert_on_enable=f"✅ New entries re-enabled: source={source}",
    )


def is_new_entries_enabled() -> bool:
    return _read_bool_flag(NEW_ENTRIES_ENABLED_KEY, default=True)


def read_new_entries_enabled() -> dict[str, Any] | None:
    return _read_flag_record(NEW_ENTRIES_ENABLED_KEY)


# exit_only_mode — block entries, allow exits/GTTs. Default False.
def set_exit_only_mode(*, enabled: bool, source: str, reason: str | None = None) -> dict[str, Any]:
    return _set_bool_flag(
        control_key=EXIT_ONLY_MODE_KEY,
        enabled=enabled,
        source=source,
        reason=reason,
        default=False,
        alert_on_disable=f"✅ Exit-only mode cleared: source={source}",
        alert_on_enable=f"⚠️ Exit-only mode engaged: reason={reason or 'unspecified'} source={source}",
    )


def is_exit_only_mode() -> bool:
    return _read_bool_flag(EXIT_ONLY_MODE_KEY, default=False)


def read_exit_only_mode() -> dict[str, Any] | None:
    return _read_flag_record(EXIT_ONLY_MODE_KEY)


# flatten_requested — operator-initiated flatten. Holds a payload while pending.
def request_flatten(
    *,
    source: str,
    reason: str,
    tickers: list[str] | None = None,
    multi_day_holdings_acked: list[str] | None = None,
) -> dict[str, Any]:
    now = _now_iso()
    normalized_tickers = sorted({str(t).strip().upper() for t in (tickers or []) if str(t).strip()})
    normalized_acked = sorted({str(t).strip().upper() for t in (multi_day_holdings_acked or []) if str(t).strip()})
    with session_scope() as session:
        repo = MemoryRepository(session)
        existing = repo.get_operator_control(FLATTEN_REQUEST_KEY)
        existing_value = dict((existing or {}).get("value", {}) or {})
        history = list(existing_value.get("history", []))
        history.append(
            {
                "event": "request",
                "at": now,
                "source": source,
                "reason": reason,
                "tickers": normalized_tickers,
                "multi_day_holdings_acked": normalized_acked,
            }
        )
        history = history[-_HISTORY_LIMIT:]
        flatten_id = f"flatten:{now}:{source}"
        value = {
            "pending": True,
            "flatten_id": flatten_id,
            "tickers": normalized_tickers or None,
            "multi_day_holdings_acked": normalized_acked,
            "reason": reason,
            "latest_source": source,
            "requested_at": now,
            "updated_at": now,
            "results": [],
            "history": history,
        }
        result = repo.upsert_operator_control(
            control_key=FLATTEN_REQUEST_KEY,
            value=value,
            payload={"type": "flatten_request"},
            source=source,
        )
        repo.append_execution_event(
            event_type="flatten_requested",
            entity_type="flatten_request",
            entity_id=flatten_id,
            source=source,
            payload={
                "tickers": normalized_tickers or None,
                "reason": reason,
                "multi_day_holdings_acked": normalized_acked,
            },
        )

    label = "all positions" if not normalized_tickers else ", ".join(normalized_tickers)
    _dispatch_control_alert(
        f"🧹 Flatten requested ({label}): reason={reason} source={source}",
        level="critical",
    )
    return result


def read_flatten_request() -> dict[str, Any] | None:
    return _read_flag_record(FLATTEN_REQUEST_KEY)


def append_flatten_result(*, ticker: str, outcome: dict[str, Any], source: str) -> dict[str, Any] | None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        existing = repo.get_operator_control(FLATTEN_REQUEST_KEY)
        if existing is None:
            return None
        value = dict(existing.get("value") or {})
        results = list(value.get("results") or [])
        results.append({"ticker": ticker, "outcome": outcome, "at": _now_iso()})
        value["results"] = results[-_HISTORY_LIMIT * 2 :]
        value["updated_at"] = _now_iso()
        result = repo.upsert_operator_control(
            control_key=FLATTEN_REQUEST_KEY,
            value=value,
            payload={"type": "flatten_request"},
            source=source,
        )
        repo.append_execution_event(
            event_type="flatten_result_recorded",
            entity_type="flatten_request",
            entity_id=str(value.get("flatten_id") or ticker),
            source=source,
            payload={"ticker": ticker, "outcome": outcome},
        )
        return result


def clear_flatten_request(*, source: str, reason: str | None = None) -> dict[str, Any] | None:
    now = _now_iso()
    with session_scope() as session:
        repo = MemoryRepository(session)
        existing = repo.get_operator_control(FLATTEN_REQUEST_KEY)
        if existing is None:
            return None
        value = dict(existing.get("value") or {})
        was_pending = bool(value.get("pending"))
        history = list(value.get("history") or [])
        history.append(
            {
                "event": "clear",
                "at": now,
                "source": source,
                "reason": reason,
                "was_pending": was_pending,
            }
        )
        history = history[-_HISTORY_LIMIT:]
        value["pending"] = False
        value["cleared_at"] = now
        value["latest_source"] = source
        value["updated_at"] = now
        value["history"] = history
        result = repo.upsert_operator_control(
            control_key=FLATTEN_REQUEST_KEY,
            value=value,
            payload={"type": "flatten_request"},
            source=source,
        )

    if was_pending:
        _dispatch_control_alert(
            f"✅ Flatten request cleared: source={source} reason={reason or 'completed'}",
            level="info",
        )
    return result


def is_flatten_requested() -> bool:
    record = read_flatten_request()
    if record is None:
        return False
    return bool(record.get("pending"))
