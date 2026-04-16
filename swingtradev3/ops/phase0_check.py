from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from auth.kite.client import (
    fetch_historical_data,
    fetch_holdings,
    fetch_margins,
    fetch_positions,
    fetch_profile,
    has_kite_session,
)
from auth.kite.websocket import probe_order_update_websocket
from config import cfg, runtime_flags
from models import AccountState
from paths import CONTEXT_DIR
from storage import read_json, write_json


STATE_PATH = CONTEXT_DIR / "state.json"
STATE_BACKUP_DIR = CONTEXT_DIR / "state_backups"


@dataclass(slots=True)
class CheckResult:
    name: str
    status: str
    detail: str


@dataclass(slots=True)
class ReconcileStateResult:
    removed_stale: list[str]
    missing_local: list[str]
    backup_path: Path | None = None


def _truthy_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _broker_position_tickers(payload: dict[str, object]) -> set[str]:
    tickers: set[str] = set()
    net_positions = payload.get("net", [])
    if isinstance(net_positions, list):
        for item in net_positions:
            if not isinstance(item, dict):
                continue
            quantity = int(item.get("quantity") or 0)
            if quantity <= 0:
                continue
            ticker = str(item.get("tradingsymbol") or "").strip().upper()
            if ticker:
                tickers.add(ticker)
    return tickers


def _holding_tickers(payload: list[dict[str, object]]) -> set[str]:
    tickers: set[str] = set()
    for item in payload:
        quantity = int(item.get("quantity") or 0) + int(item.get("t1_quantity") or 0)
        if quantity <= 0:
            continue
        ticker = str(item.get("tradingsymbol") or "").strip().upper()
        if ticker:
            tickers.add(ticker)
    return tickers


def _local_state_tickers() -> set[str]:
    state_data = read_json(STATE_PATH, {})
    positions = state_data.get("positions", []) if isinstance(state_data, dict) else []
    tickers: set[str] = set()
    if isinstance(positions, list):
        for item in positions:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker") or "").strip().upper()
            if ticker:
                tickers.add(ticker)
    return tickers


def _broker_tickers() -> set[str]:
    broker_positions = _broker_position_tickers(fetch_positions())
    broker_holdings = _holding_tickers(fetch_holdings())
    return broker_positions | broker_holdings


def _backup_state_file(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_path = STATE_BACKUP_DIR / f"state.{timestamp}.json"
    STATE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_path)
    return backup_path


def _run_check(name: str, fn: Callable[[], CheckResult]) -> CheckResult:
    try:
        return fn()
    except Exception as exc:
        return CheckResult(name=name, status="FAIL", detail=str(exc))


def check_runtime_guardrails() -> CheckResult:
    mode = cfg.trading.mode.value
    live_enabled = runtime_flags.live_trading_enabled
    entries_enabled = runtime_flags.new_entries_enabled
    exit_only = runtime_flags.exit_only_mode

    if entries_enabled and not live_enabled:
        return CheckResult(
            name="runtime_guardrails",
            status="FAIL",
            detail="NEW_ENTRIES_ENABLED=true while LIVE_TRADING_ENABLED=false",
        )
    if entries_enabled and exit_only:
        return CheckResult(
            name="runtime_guardrails",
            status="FAIL",
            detail="NEW_ENTRIES_ENABLED=true while EXIT_ONLY_MODE=true",
        )
    return CheckResult(
        name="runtime_guardrails",
        status="PASS",
        detail=(
            f"mode={mode}, live_enabled={live_enabled}, "
            f"new_entries_enabled={entries_enabled}, exit_only={exit_only}"
        ),
    )


def check_kite_session() -> CheckResult:
    if not has_kite_session():
        return CheckResult(
            name="kite_session",
            status="FAIL",
            detail="No persisted Kite session or KITE_ACCESS_TOKEN is available",
        )
    return CheckResult(
        name="kite_session",
        status="PASS",
        detail="Persisted Kite session is present",
    )


def check_profile() -> CheckResult:
    profile = fetch_profile()
    user_id = str(profile.get("user_id") or "unknown")
    broker = str(profile.get("broker") or "unknown")
    return CheckResult(
        name="kite_profile",
        status="PASS",
        detail=f"user_id={user_id}, broker={broker}",
    )


def check_positions() -> CheckResult:
    positions = fetch_positions()
    open_count = len(_broker_position_tickers(positions))
    return CheckResult(
        name="broker_positions",
        status="PASS",
        detail=f"open_position_symbols={open_count}",
    )


def check_holdings() -> CheckResult:
    holdings = fetch_holdings()
    holding_count = len(_holding_tickers(holdings))
    return CheckResult(
        name="broker_holdings",
        status="PASS",
        detail=f"holding_symbols={holding_count}",
    )


def check_margins() -> CheckResult:
    margins = fetch_margins()
    equity = margins.get("equity", {}) if isinstance(margins, dict) else {}
    available = equity.get("available", {}) if isinstance(equity, dict) else {}
    cash = available.get("cash")
    if cash is None:
        return CheckResult(
            name="broker_margins",
            status="PASS",
            detail="Margins endpoint reachable",
        )
    return CheckResult(
        name="broker_margins",
        status="PASS",
        detail=f"available_cash={cash}",
    )


def check_paid_data_access() -> CheckResult:
    candles = fetch_historical_data(
        ticker="RELIANCE",
        exchange=cfg.trading.exchange,
        interval="day",
        lookback_days=5,
    )
    count = len(candles)
    if count == 0:
        return CheckResult(
            name="paid_data_access",
            status="FAIL",
            detail="Historical data returned no candles for RELIANCE",
        )
    return CheckResult(
        name="paid_data_access",
        status="PASS",
        detail=f"historical_candles={count}",
    )


def check_state_sync() -> CheckResult:
    local = _local_state_tickers()
    broker = _broker_tickers()
    if local == broker:
        return CheckResult(
            name="local_state_alignment",
            status="PASS",
            detail=f"symbols={sorted(local)}",
        )
    missing_local = sorted(broker - local)
    stale_local = sorted(local - broker)
    return CheckResult(
        name="local_state_alignment",
        status="WARN",
        detail=f"missing_local={missing_local}, stale_local={stale_local}",
    )


def check_ddpi_poa() -> CheckResult:
    if has_kite_session():
        profile = fetch_profile()
        meta = profile.get("meta", {}) if isinstance(profile, dict) else {}
        demat_consent = ""
        if isinstance(meta, dict):
            demat_consent = str(meta.get("demat_consent") or "").strip().lower()
        if demat_consent == "physical":
            return CheckResult(
                name="ddpi_poa",
                status="PASS",
                detail="Broker profile indicates holdings authorisation is fully enabled (demat_consent=physical)",
            )
        if demat_consent == "consent":
            return CheckResult(
                name="ddpi_poa",
                status="WARN",
                detail="Broker profile still requires holdings authorisation (demat_consent=consent)",
            )
    if _truthy_env("KITE_DDPI_POA_CONFIRMED", False):
        return CheckResult(
            name="ddpi_poa",
            status="PASS",
            detail="DDPI/POA manually confirmed by environment override",
        )
    return CheckResult(
        name="ddpi_poa",
        status="WARN",
        detail="DDPI/POA not confirmed; multi-day unattended exits must remain disabled",
    )


def check_websocket_readiness() -> CheckResult:
    if not has_kite_session():
        return CheckResult(
            name="websocket_order_updates",
            status="FAIL",
            detail="No Kite session available for WebSocket readiness probe",
        )
    result = probe_order_update_websocket()
    if not result.connected:
        return CheckResult(
            name="websocket_order_updates",
            status="FAIL",
            detail=result.error or "Broker WebSocket probe did not connect",
        )
    return CheckResult(
        name="websocket_order_updates",
        status="PASS",
        detail=(
            "Connected to broker WebSocket with order-update callback registered"
            f" (close_code={result.close_code}, close_reason={result.close_reason or 'n/a'})"
        ),
    )


def reconcile_local_state() -> ReconcileStateResult:
    state_payload = read_json(STATE_PATH, {})
    state = AccountState.model_validate(state_payload if isinstance(state_payload, dict) else {})
    broker = _broker_tickers()
    local = {position.ticker.upper() for position in state.positions}

    stale_local = sorted(local - broker)
    missing_local = sorted(broker - local)
    backup_path: Path | None = None

    if stale_local:
        if STATE_PATH.exists():
            backup_path = _backup_state_file(STATE_PATH)
        state.positions = [
            position for position in state.positions if position.ticker.upper() not in set(stale_local)
        ]
        write_json(STATE_PATH, state.model_dump(mode="json"))

    return ReconcileStateResult(
        removed_stale=stale_local,
        missing_local=missing_local,
        backup_path=backup_path,
    )


def format_reconcile_report(result: ReconcileStateResult) -> str:
    backup_detail = f", backup={result.backup_path}" if result.backup_path else ""
    removed = result.removed_stale or ["none"]
    missing = result.missing_local or ["none"]
    return (
        "Phase 0 Local State Reconciliation\n"
        f"removed_stale={removed}{backup_detail}\n"
        f"missing_local={missing}"
    )


def run_phase0_checks() -> list[CheckResult]:
    checks = [
        ("runtime_guardrails", check_runtime_guardrails),
        ("kite_session", check_kite_session),
        ("kite_profile", check_profile),
        ("broker_positions", check_positions),
        ("broker_holdings", check_holdings),
        ("broker_margins", check_margins),
        ("paid_data_access", check_paid_data_access),
        ("local_state_alignment", check_state_sync),
        ("ddpi_poa", check_ddpi_poa),
        ("websocket_order_updates", check_websocket_readiness),
    ]

    results: list[CheckResult] = []
    session_ok = True
    for name, fn in checks:
        if name not in {"runtime_guardrails", "ddpi_poa"} and not session_ok:
            results.append(
                CheckResult(name=name, status="FAIL", detail="Skipped because Kite session check failed")
            )
            continue
        result = _run_check(name, fn)
        results.append(result)
        if name == "kite_session" and result.status == "FAIL":
            session_ok = False
    return results


def format_report(results: list[CheckResult]) -> str:
    lines = ["Phase 0 Preflight", ""]
    for result in results:
        lines.append(f"[{result.status}] {result.name}: {result.detail}")
    fail_count = sum(1 for result in results if result.status == "FAIL")
    warn_count = sum(1 for result in results if result.status == "WARN")
    lines.extend(
        [
            "",
            f"Summary: {fail_count} fail, {warn_count} warn",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    results = run_phase0_checks()
    print(format_report(results))
    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
