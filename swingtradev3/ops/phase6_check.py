"""Phase 6 operator runbook.

Prints current reconciliation health:
- block_new_entries state and active reasons
- last startup reconciliation
- recent reconciliation_runs per loop
- open failure incidents
- tracked positions and their lifecycle_state distribution
- quote freshness / stream connectivity (best-effort)

Exits non-zero if any of:
- block_new_entries is active
- an open critical incident exists
- a position is in ``reconcile_required`` or ``operator_intervention``

Run via ``make phase6-check``.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select

from execution.operator_controls import (
    active_block_reasons,
    is_block_new_entries_active,
    read_block_new_entries,
    read_reconciliation_status,
)
from memory.db import session_scope
from memory.models import ReconciliationRunRow
from memory.repositories import MemoryRepository


@dataclass(slots=True)
class CheckResult:
    name: str
    status: str  # PASS | WARN | FAIL
    detail: str


def check_block_new_entries() -> CheckResult:
    if not is_block_new_entries_active():
        return CheckResult(
            name="block_new_entries",
            status="PASS",
            detail="no active reasons; entries are permitted",
        )
    record = read_block_new_entries() or {}
    reasons = active_block_reasons()
    latest = record.get("latest_reason") or "?"
    return CheckResult(
        name="block_new_entries",
        status="FAIL",
        detail=f"active reasons={reasons}; latest={latest}; source={record.get('latest_source')}",
    )


def check_reconciliation_status() -> CheckResult:
    status = read_reconciliation_status()
    if status is None:
        return CheckResult(
            name="reconciliation_status",
            status="WARN",
            detail="no reconciliation_status operator control has been written yet",
        )
    phase = status.get("phase")
    return CheckResult(
        name="reconciliation_status",
        status="PASS",
        detail=(
            f"phase={phase} stale_ratio={status.get('stale_ratio')} "
            f"stream_connected={status.get('stream_connected')} "
            f"tickers={len(status.get('tickers', []) or [])}"
        ),
    )


def check_recent_runs() -> CheckResult:
    with session_scope() as session:
        rows = (
            session.scalars(
                select(ReconciliationRunRow)
                .order_by(ReconciliationRunRow.updated_at.desc())
                .limit(50)
            ).all()
        )
    if not rows:
        return CheckResult(
            name="recent_reconciliation_runs",
            status="WARN",
            detail="no reconciliation_runs persisted; worker may not be running",
        )
    per_kind_latest: dict[str, tuple[str, str]] = {}
    for row in rows:
        parts = row.reconciliation_run_id.split(":")
        kind = parts[1] if len(parts) >= 2 else row.reconciliation_run_id
        if kind in per_kind_latest:
            continue
        per_kind_latest[kind] = (
            row.status,
            row.updated_at.isoformat() if row.updated_at else "?",
        )
    details = " ".join(
        f"{kind}={status}@{ts}" for kind, (status, ts) in sorted(per_kind_latest.items())
    )
    any_failed = any(status == "failed" for status, _ in per_kind_latest.values())
    return CheckResult(
        name="recent_reconciliation_runs",
        status="WARN" if any_failed else "PASS",
        detail=details,
    )


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


def check_position_states() -> CheckResult:
    with session_scope() as session:
        repo = MemoryRepository(session)
        positions = repo.list_positions()
    if not positions:
        return CheckResult(
            name="position_states",
            status="PASS",
            detail="no open positions",
        )
    counts: Counter[str] = Counter(str(p.get("state") or "?") for p in positions)
    flagged = counts.get("reconcile_required", 0) + counts.get("operator_intervention", 0)
    breakdown = ", ".join(f"{state}={count}" for state, count in sorted(counts.items()))
    return CheckResult(
        name="position_states",
        status="FAIL" if flagged else "PASS",
        detail=f"total={len(positions)} {breakdown}",
    )


def run_checks() -> list[CheckResult]:
    return [
        check_block_new_entries(),
        check_reconciliation_status(),
        check_recent_runs(),
        check_incidents(),
        check_position_states(),
    ]


def format_report(results: list[CheckResult]) -> str:
    lines = ["PHASE 6 CHECK", "=" * 48]
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
