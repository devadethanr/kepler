from __future__ import annotations

from dataclasses import dataclass

from auth.kite.client import has_kite_session
from broker.reducer import BrokerReducer
from memory.db import session_scope
from memory.repositories import MemoryRepository
from paths import CONTEXT_DIR
from storage import read_json


STATE_PATH = CONTEXT_DIR / "state.json"


@dataclass(slots=True)
class CheckResult:
    name: str
    status: str
    detail: str


def check_kite_session() -> CheckResult:
    if not has_kite_session():
        return CheckResult(
            name="kite_session",
            status="FAIL",
            detail="No valid persisted Kite session is available for Phase 3 broker validation",
        )
    return CheckResult(
        name="kite_session",
        status="PASS",
        detail="Valid persisted Kite session is present",
    )


def check_broker_sync_roundtrip() -> CheckResult:
    reducer = BrokerReducer()
    first = reducer.sync_from_broker(source="phase3_check_first")
    second = reducer.sync_from_broker(source="phase3_check_second")
    return CheckResult(
        name="broker_sync_roundtrip",
        status="PASS",
        detail=(
            f"orders={first['orders']['applied']}/{second['orders']['deduplicated']} "
            f"gtts={first['gtts']['applied']}/{second['gtts']['deduplicated']} "
            f"positions={first['positions']['positions']} "
            f"tracked_tickers={len(first['tracked_tickers'])}"
        ),
    )


def check_reconstructed_state_shape() -> CheckResult:
    state = read_json(STATE_PATH, {})
    positions = state.get("positions", []) if isinstance(state, dict) else []
    legacy_dual_ids = [
        str(item.get("ticker") or "")
        for item in positions
        if isinstance(item, dict)
        and (item.get("stop_gtt_id") is not None or item.get("target_gtt_id") is not None)
    ]
    if legacy_dual_ids:
        return CheckResult(
            name="reconstructed_state_shape",
            status="FAIL",
            detail=f"Legacy stop/target GTT ids still present for: {', '.join(sorted(legacy_dual_ids))}",
        )
    return CheckResult(
        name="reconstructed_state_shape",
        status="PASS",
        detail=f"positions={len(positions)}",
    )


def check_persisted_broker_rows() -> CheckResult:
    with session_scope() as session:
        repo = MemoryRepository(session)
        broker_orders = len(repo.list_broker_orders())
        protective_triggers = len(repo.list_protective_triggers())
        order_intents = len(repo.list_order_intents())
    return CheckResult(
        name="persisted_broker_rows",
        status="PASS",
        detail=(
            f"broker_orders={broker_orders}, protective_triggers={protective_triggers}, "
            f"order_intents={order_intents}"
        ),
    )


def run_checks() -> list[CheckResult]:
    checks = [check_kite_session()]
    if checks[0].status == "FAIL":
        return checks
    checks.extend(
        [
            check_broker_sync_roundtrip(),
            check_reconstructed_state_shape(),
            check_persisted_broker_rows(),
        ]
    )
    return checks


def format_report(results: list[CheckResult]) -> str:
    lines = ["PHASE 3 CHECK", "=" * 40]
    for result in results:
        lines.append(f"[{result.status}] {result.name}: {result.detail}")
    fail_count = sum(1 for result in results if result.status == "FAIL")
    lines.append("-" * 40)
    lines.append(f"failures={fail_count}")
    return "\n".join(lines)


def main() -> int:
    results = run_checks()
    report = format_report(results)
    print(report)
    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
