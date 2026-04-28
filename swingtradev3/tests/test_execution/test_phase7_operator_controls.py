"""Phase 7 (P14): operator-control flag tests.

Covers the four new first-class flags (``trading_enabled``,
``new_entries_enabled``, ``exit_only_mode``, ``flatten_requested``) and their
interaction with the Phase 6 ``block_new_entries`` multi-reason set.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from execution.operator_controls import (
    active_block_reasons,
    clear_block_new_entries,
    clear_flatten_request,
    is_block_new_entries_active,
    is_exit_only_mode,
    is_flatten_requested,
    is_new_entries_enabled,
    is_trading_enabled,
    read_exit_only_mode,
    read_flatten_request,
    read_new_entries_enabled,
    read_trading_enabled,
    request_flatten,
    set_block_new_entries,
    set_exit_only_mode,
    set_new_entries_enabled,
    set_trading_enabled,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_operator_controls():
    # Reset flags to defaults before and after every test.
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_trading_enabled(enabled=True, source="test_reset")
        set_new_entries_enabled(enabled=True, source="test_reset")
        set_exit_only_mode(enabled=False, source="test_reset")
        clear_flatten_request(source="test_reset")
        clear_block_new_entries(source="test_reset")
    yield
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_trading_enabled(enabled=True, source="test_reset")
        set_new_entries_enabled(enabled=True, source="test_reset")
        set_exit_only_mode(enabled=False, source="test_reset")
        clear_flatten_request(source="test_reset")
        clear_block_new_entries(source="test_reset")


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


def test_trading_enabled_default_true(monkeypatch):
    # After fixture reset, trading_enabled is True.
    assert is_trading_enabled() is True


def test_new_entries_enabled_default_true():
    assert is_new_entries_enabled() is True


def test_exit_only_mode_default_false():
    assert is_exit_only_mode() is False


def test_flatten_requested_default_false():
    assert is_flatten_requested() is False


# ---------------------------------------------------------------------------
# Setting flags + history/alerts
# ---------------------------------------------------------------------------


def test_set_trading_enabled_false_records_alert():
    with patch("execution.operator_controls._dispatch_control_alert") as mock_alert:
        set_trading_enabled(enabled=False, source="test", reason="maintenance")
    assert is_trading_enabled() is False
    mock_alert.assert_called_once()
    args = mock_alert.call_args
    assert args.kwargs.get("level") == "critical" or args[1].get("level") == "critical"


def test_set_trading_enabled_true_records_history():
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_trading_enabled(enabled=False, source="test", reason="maintenance")
        set_trading_enabled(enabled=True, source="test", reason="resume")
    record = read_trading_enabled()
    assert record is not None
    history = record.get("history") or []
    assert len(history) >= 2
    assert history[-1]["enabled"] is True
    assert history[-1]["reason"] == "resume"


def test_exit_only_mode_set_true():
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_exit_only_mode(enabled=True, source="test", reason="risk_off")
    assert is_exit_only_mode() is True
    record = read_exit_only_mode()
    assert record["latest_reason"] == "risk_off"


def test_new_entries_enabled_set_false():
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_new_entries_enabled(enabled=False, source="operator", reason="investigation")
    assert is_new_entries_enabled() is False
    record = read_new_entries_enabled()
    assert record["latest_reason"] == "investigation"


def test_same_value_set_twice_is_idempotent_for_alerts():
    with patch("execution.operator_controls._dispatch_control_alert") as mock_alert:
        set_trading_enabled(enabled=False, source="test", reason="first")
        set_trading_enabled(enabled=False, source="test", reason="second")
    # Only the first transition (True -> False) should fire an alert.
    assert mock_alert.call_count == 1


# ---------------------------------------------------------------------------
# Orthogonal to block_new_entries (multi-reason)
# ---------------------------------------------------------------------------


def test_new_entries_enabled_orthogonal_to_block():
    """block_new_entries is the automatic kill switch; new_entries_enabled is the
    operator hard-off. They persist independently."""
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_block_new_entries(reason="stale_quotes", source="reconciler")
        set_new_entries_enabled(enabled=False, source="operator", reason="manual_off")
    assert is_block_new_entries_active() is True
    assert "stale_quotes" in active_block_reasons()
    assert is_new_entries_enabled() is False

    with patch("execution.operator_controls._dispatch_control_alert"):
        clear_block_new_entries(source="reconciler", reason="stale_quotes")
    assert is_block_new_entries_active() is False
    # Operator off remains on until explicitly re-enabled.
    assert is_new_entries_enabled() is False


# ---------------------------------------------------------------------------
# Flatten request lifecycle
# ---------------------------------------------------------------------------


def test_flatten_request_writes_pending_state():
    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="operator_flatten", tickers=["RELIANCE"])
    assert is_flatten_requested() is True
    record = read_flatten_request()
    assert record["pending"] is True
    assert record["tickers"] == ["RELIANCE"]
    assert record["reason"] == "operator_flatten"


def test_flatten_request_null_tickers_means_all():
    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="kill_everything")
    record = read_flatten_request()
    assert record["tickers"] is None
    assert record["pending"] is True


def test_clear_flatten_request_resets_pending():
    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="test", tickers=["TCS"])
        clear_flatten_request(source="test", reason="cancelled")
    assert is_flatten_requested() is False
    record = read_flatten_request()
    assert record["pending"] is False
    assert record["cleared_at"] is not None


def test_flatten_request_preserves_multi_day_acks():
    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(
            source="api",
            reason="manual",
            tickers=["RELIANCE", "TCS"],
            multi_day_holdings_acked=["RELIANCE"],
        )
    record = read_flatten_request()
    assert record["multi_day_holdings_acked"] == ["RELIANCE"]


def test_flatten_request_normalizes_tickers_uppercase():
    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="test", tickers=["reliance", "tcs"])
    record = read_flatten_request()
    assert record["tickers"] == ["RELIANCE", "TCS"]
