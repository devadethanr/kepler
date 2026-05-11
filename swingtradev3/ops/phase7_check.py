"""Phase 7 operator runbook.

Prints safety-substrate health:
- Operator-control flags (trading_enabled, new_entries_enabled, exit_only_mode)
- Flatten request state (pending / none / results)
- Each of the seven automatic kill switches
- Auth session age and freshness
- DDPI/POA status
- Open failure incidents

Exits non-zero if any of:
- block_new_entries is active
- an open critical incident exists
- auth session is stale or missing
- a flatten request is pending (operator action in-flight)

Run via ``make phase7-check``.
"""
from __future__ import annotations

from dataclasses import dataclass

from execution.auth_preflight import is_session_fresh, read_auth_session_age_hours
from execution.operator_controls import (
    active_block_reasons,
    is_block_new_entries_active,
    is_exit_only_mode,
    is_new_entries_enabled,
    is_trading_enabled,
    read_block_new_entries,
    read_flatten_request,
)
from memory.db import session_scope
from memory.repository import MemoryRepository


@dataclass(slots=True)
class CheckResult:
    name: str
    status: str  # PASS | WARN | FAIL
    detail: str


KNOWN_KILL_SWITCHES = (
    "broker_disconnected",
    "stream_unavailable",
    "stale_auth",
    "stale_quotes",
    "daily_loss_limit",
    "order_submission_failures",
    "gtt_recovery_failures",
    "positions_drift",
    "orders_drift",
    "gtts_drift",
)


def check_operator_flags() -> CheckResult:
    trading = is_trading_enabled()
    new_entries = is_new_entries_enabled()
    exit_only = is_exit_only_mode()
    detail = (
        f"trading_enabled={trading} new_entries_enabled={new_entries} "
        f"exit_only_mode={exit_only}"
    )
    if not trading:
        return CheckResult(name="operator_flags", status="FAIL", detail=detail)
    if not new_entries or exit_only:
        return CheckResult(name="operator_flags", status="WARN", detail=detail)
    return CheckResult(name="operator_flags", status="PASS", detail=detail)


def check_kill_switches() -> CheckResult:
    if not is_block_new_entries_active():
        return CheckResult(
            name="kill_switches",
            status="PASS",
            detail="no active kill-switch reasons",
        )
    record = read_block_new_entries() or {}
    reasons = active_block_reasons()
    unknown = [r for r in reasons if r not in KNOWN_KILL_SWITCHES]
    unknown_note = f"; unknown_reasons={unknown}" if unknown else ""
    return CheckResult(
        name="kill_switches",
        status="FAIL",
        detail=(
            f"reasons={reasons} latest={record.get('latest_reason')} "
            f"source={record.get('latest_source')}{unknown_note}"
        ),
    )


def check_flatten_request() -> CheckResult:
    request = read_flatten_request()
    if not request:
        return CheckResult(
            name="flatten_request",
            status="PASS",
            detail="no flatten request history",
        )
    if request.get("pending"):
        return CheckResult(
            name="flatten_request",
            status="FAIL",
            detail=(
                f"pending flatten: tickers={request.get('tickers')} "
                f"reason={request.get('reason')} requested_at={request.get('requested_at')}"
            ),
        )
    return CheckResult(
        name="flatten_request",
        status="PASS",
        detail=(
            f"not pending; last_cleared_at={request.get('cleared_at')} "
            f"results={len(request.get('results') or [])}"
        ),
    )


def check_auth() -> CheckResult:
    fresh, reason, age_hours = is_session_fresh()
    if age_hours is None:
        age_hours = read_auth_session_age_hours()
    if fresh:
        return CheckResult(
            name="auth_session",
            status="PASS",
            detail=f"fresh; age_hours={age_hours}",
        )
    return CheckResult(
        name="auth_session",
        status="FAIL",
        detail=f"stale; reason={reason} age_hours={age_hours}",
    )


def check_ddpi() -> CheckResult:
    try:
        from ops.phase0_check import check_ddpi_poa

        result = check_ddpi_poa()
    except Exception as exc:  # pragma: no cover
        return CheckResult(name="ddpi_poa", status="WARN", detail=f"probe failed: {exc}")
    return CheckResult(name="ddpi_poa", status=result.status, detail=result.detail)


def check_incidents() -> CheckResult:
    with session_scope() as session:
        repo = MemoryRepository(session)
        open_incidents = repo.list_failure_incidents(status="open")
    if not open_incidents:
        return CheckResult(
            name="open_incidents",
            status="PASS",
            detail="0 open incidents",
        )
    critical = [i for i in open_incidents if i.get("severity") == "critical"]
    summary = ", ".join(
        f"{i.get('incident_id')}({i.get('severity')})" for i in open_incidents[:8]
    )
    return CheckResult(
        name="open_incidents",
        status="FAIL" if critical else "WARN",
        detail=f"total={len(open_incidents)} critical={len(critical)}: {summary}",
    )


def run_checks() -> list[CheckResult]:
    return [
        check_operator_flags(),
        check_kill_switches(),
        check_flatten_request(),
        check_auth(),
        check_ddpi(),
        check_incidents(),
    ]


def format_report(results: list[CheckResult]) -> str:
    lines = ["PHASE 7 CHECK", "=" * 48]
    for result in results:
        lines.append(f"[{result.status}] {result.name}: {result.detail}")
    fail_count = sum(1 for r in results if r.status == "FAIL")
    warn_count = sum(1 for r in results if r.status == "WARN")
    lines.append("-" * 48)
    lines.append(f"failures={fail_count} warnings={warn_count}")
    return "\n".join(lines)


def main() -> int:
    results = run_checks()
    print(format_report(results))
    return 1 if any(r.status == "FAIL" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
