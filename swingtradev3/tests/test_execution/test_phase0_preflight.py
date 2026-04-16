from __future__ import annotations

from pathlib import Path

from ops.phase0_check import (
    CheckResult,
    check_ddpi_poa,
    format_reconcile_report,
    format_report,
    reconcile_local_state,
    run_phase0_checks,
)


def test_phase0_preflight_stops_broker_checks_when_session_missing(monkeypatch):
    monkeypatch.setattr("ops.phase0_check.has_kite_session", lambda: False)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "false")
    monkeypatch.setenv("EXIT_ONLY_MODE", "false")

    results = run_phase0_checks()
    by_name = {result.name: result for result in results}

    assert by_name["runtime_guardrails"].status == "PASS"
    assert by_name["kite_session"].status == "FAIL"
    assert by_name["kite_profile"].detail.startswith("Skipped because Kite session check failed")
    assert by_name["broker_positions"].detail.startswith("Skipped because Kite session check failed")


def test_phase0_preflight_reports_ddpi_as_warning_by_default(monkeypatch):
    monkeypatch.setattr("ops.phase0_check.has_kite_session", lambda: False)
    monkeypatch.delenv("KITE_DDPI_POA_CONFIRMED", raising=False)

    results = run_phase0_checks()
    by_name = {result.name: result for result in results}

    assert by_name["ddpi_poa"].status == "WARN"
    assert "must remain disabled" in by_name["ddpi_poa"].detail


def test_phase0_preflight_uses_profile_truth_for_ddpi(monkeypatch):
    monkeypatch.setattr("ops.phase0_check.has_kite_session", lambda: True)
    monkeypatch.setattr(
        "ops.phase0_check.fetch_profile",
        lambda: {"meta": {"demat_consent": "consent"}},
    )
    monkeypatch.setenv("KITE_DDPI_POA_CONFIRMED", "true")

    result = check_ddpi_poa()

    assert result.status == "WARN"
    assert "demat_consent=consent" in result.detail


def test_phase0_preflight_happy_path(monkeypatch):
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "false")
    monkeypatch.setenv("EXIT_ONLY_MODE", "true")

    monkeypatch.setattr("ops.phase0_check.has_kite_session", lambda: True)
    monkeypatch.setattr(
        "ops.phase0_check.fetch_profile",
        lambda: {
            "user_id": "AB1234",
            "broker": "zerodha",
            "meta": {"demat_consent": "physical"},
        },
    )
    monkeypatch.setattr(
        "ops.phase0_check.fetch_positions",
        lambda: {"net": [{"tradingsymbol": "RELIANCE", "quantity": 1}]},
    )
    monkeypatch.setattr(
        "ops.phase0_check.fetch_holdings",
        lambda: [{"tradingsymbol": "RELIANCE", "quantity": 1, "t1_quantity": 0}],
    )
    monkeypatch.setattr(
        "ops.phase0_check.fetch_margins",
        lambda: {"equity": {"available": {"cash": 12345}}},
    )
    monkeypatch.setattr(
        "ops.phase0_check.fetch_historical_data",
        lambda **_kwargs: [{"close": 1}, {"close": 2}],
    )
    monkeypatch.setattr(
        "ops.phase0_check.read_json",
        lambda *_args, **_kwargs: {"positions": [{"ticker": "RELIANCE"}]},
    )
    monkeypatch.setattr(
        "ops.phase0_check.check_websocket_readiness",
        lambda: CheckResult(
            name="websocket_order_updates",
            status="WARN",
            detail="Not enabled in test",
        ),
    )

    results = run_phase0_checks()
    by_name = {result.name: result for result in results}

    assert by_name["kite_session"].status == "PASS"
    assert by_name["kite_profile"].status == "PASS"
    assert by_name["broker_positions"].status == "PASS"
    assert by_name["broker_holdings"].status == "PASS"
    assert by_name["broker_margins"].status == "PASS"
    assert by_name["paid_data_access"].status == "PASS"
    assert by_name["local_state_alignment"].status == "PASS"
    assert by_name["ddpi_poa"].status == "PASS"


def test_reconcile_local_state_removes_stale_positions(monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    backup_dir = tmp_path / "backups"
    state_path.write_text(
        (
            '{"cash_inr": 50000.0, "positions": ['
            '{"ticker": "SBIN", "quantity": 10, "entry_price": 800.0, "current_price": 850.0, '
            '"stop_price": 791.81, "target_price": 900.0, "opened_at": "2026-04-01T10:00:00"}'
            ']}'
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("ops.phase0_check.STATE_PATH", state_path)
    monkeypatch.setattr("ops.phase0_check.STATE_BACKUP_DIR", backup_dir)
    monkeypatch.setattr("ops.phase0_check.fetch_positions", lambda: {"net": []})
    monkeypatch.setattr("ops.phase0_check.fetch_holdings", lambda: [])

    result = reconcile_local_state()

    assert result.removed_stale == ["SBIN"]
    assert result.missing_local == []
    assert result.backup_path is not None
    payload = state_path.read_text(encoding="utf-8")
    assert '"positions": []' in payload


def test_format_reconcile_report():
    report = format_reconcile_report(
        type(
            "Result",
            (),
            {
                "removed_stale": ["SBIN"],
                "missing_local": [],
                "backup_path": Path("/tmp/state.backup.json"),
            },
        )()
    )

    assert "Phase 0 Local State Reconciliation" in report
    assert "removed_stale=['SBIN']" in report
    assert "backup=/tmp/state.backup.json" in report
    assert "missing_local=['none']" in report


def test_phase0_preflight_format_report():
    report = format_report(
        [
            CheckResult(name="a", status="PASS", detail="ok"),
            CheckResult(name="b", status="WARN", detail="careful"),
            CheckResult(name="c", status="FAIL", detail="bad"),
        ]
    )

    assert "Phase 0 Preflight" in report
    assert "[PASS] a: ok" in report
    assert "[WARN] b: careful" in report
    assert "[FAIL] c: bad" in report
    assert "Summary: 1 fail, 1 warn" in report
