from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from api.main import app
from config import cfg
from execution.operator_controls import set_new_entries_enabled
from execution.trailing_engine import TrailingEngine
from memory.db import session_scope
from memory.models import ExecutionEventRow, PolicyOverlayRow
from models import AccountState, PositionState
from policy.bounds import PolicyValidationError, validate_policy_value
from policy.effective_policy import resolve_effective_policy
from policy.governor import PolicyGovernor
from regime_adapter import RegimeAdaptiveConfig
from risk.engine import SelfHealingRiskEngine
from risk.position_sizer import capital_fraction_from_score

IST = ZoneInfo("Asia/Kolkata")
client = TestClient(app)


@pytest.fixture(autouse=True)
def phase10_cleanup():
    with (
        patch.object(cfg.api, "enabled", False),
        patch("execution.operator_controls._dispatch_control_alert"),
    ):
        set_new_entries_enabled(enabled=True, source="test_phase10_reset")
        yield
        set_new_entries_enabled(enabled=True, source="test_phase10_reset")

    with session_scope() as session:
        for row in (
            session.query(PolicyOverlayRow)
            .filter(PolicyOverlayRow.overlay_id.like("phase10-%"))
            .all()
        ):
            session.delete(row)
        for row in (
            session.query(ExecutionEventRow)
            .filter(ExecutionEventRow.entity_id.like("phase10-%"))
            .all()
        ):
            session.delete(row)


def _activate(
    key: str,
    value: object,
    *,
    overlay_id: str,
    expires_at: str | None = None,
):
    governor = PolicyGovernor()
    governor.propose_overlay(
        key=key,
        value=value,
        reason="phase 10 test",
        proposer="pytest",
        overlay_id=overlay_id,
        expires_at=expires_at,
    )
    return governor.approve_overlay(overlay_id, approver="pytest")


def test_phase10_bounds_reject_unknown_and_unsafe_values():
    with pytest.raises(PolicyValidationError):
        validate_policy_value("risk.freeform", 1)
    with pytest.raises(PolicyValidationError):
        validate_policy_value("max_position_size_pct", 90)
    with pytest.raises(PolicyValidationError):
        validate_policy_value("new_entries_enabled", "false")
    with pytest.raises(PolicyValidationError):
        validate_policy_value(
            "trail_to_pct",
            4,
            current_policy={"trail_stop_at_pct": 5, "trail_to_pct": 10},
        )


def test_phase10_overlay_lifecycle_is_auditable_and_reversible():
    governor = PolicyGovernor()
    proposed = governor.propose_overlay(
        key="min_score_threshold",
        value=8.5,
        reason="tighten entries",
        proposer="pytest",
        overlay_id="phase10-min-score",
    )

    assert proposed.status == "proposed"
    assert resolve_effective_policy().min_score_threshold == cfg.research.min_score_threshold

    active = governor.approve_overlay("phase10-min-score", approver="operator")
    assert active.status == "active"
    policy = resolve_effective_policy()
    assert policy.min_score_threshold == 8.5
    assert policy.sources["min_score_threshold"] == "policy_overlay:phase10-min-score"

    rolled_back = governor.rollback_overlay(
        "phase10-min-score",
        actor="operator",
        reason="test complete",
    )
    assert rolled_back.status == "rolled_back"
    assert resolve_effective_policy().min_score_threshold == cfg.research.min_score_threshold


def test_phase10_expired_overlays_are_ignored():
    expired_at = (datetime.now(IST) - timedelta(minutes=1)).isoformat()
    _activate(
        "max_position_size_pct",
        10,
        overlay_id="phase10-expired-size",
        expires_at=expired_at,
    )

    policy = resolve_effective_policy()

    assert policy.max_position_size_pct == cfg.risk.max_position_size_pct
    assert policy.ignored_overlays[0].reason == "expired"
    dashboard = client.get("/dashboard/policy")
    assert dashboard.status_code == 200
    assert dashboard.json()["active_overlays"] == []


def test_phase10_operator_control_vetoes_new_entries_overlay():
    _activate("new_entries_enabled", True, overlay_id="phase10-enable-entries")
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_new_entries_enabled(enabled=False, source="operator", reason="manual off")

    policy = resolve_effective_policy()

    assert policy.new_entries_enabled is False
    assert policy.sources["new_entries_enabled"] == "operator_control:new_entries_enabled"


def test_phase10_policy_caps_position_sizing_and_sector_concentration():
    _activate("max_position_size_pct", 10, overlay_id="phase10-position-cap")
    _activate("max_same_sector_positions", 1, overlay_id="phase10-sector-cap")

    assert capital_fraction_from_score(9.0) == 0.10

    state = AccountState(
        cash_inr=100000,
        positions=[
            PositionState(
                ticker="TCS",
                quantity=1,
                entry_price=1000,
                current_price=1000,
                stop_price=950,
                target_price=1120,
                opened_at=datetime.now(),
                sector="IT",
            )
        ],
    )
    decision = SelfHealingRiskEngine().evaluate(
        state,
        score=9.0,
        entry_price=1000,
        stop_price=950,
        target_price=1120,
        sector="IT",
    )

    assert decision.approved is False
    assert decision.reason == "max_same_sector_positions"


def test_phase10_research_and_trailing_paths_use_effective_policy():
    _activate("min_score_threshold", 8.5, overlay_id="phase10-regime-score")
    _activate("trail_stop_at_pct", 3, overlay_id="phase10-trail-stop")

    assert RegimeAdaptiveConfig("bull").min_entry_score() == 8.5

    position = PositionState(
        ticker="INFY",
        quantity=1,
        entry_price=1000,
        current_price=1000,
        stop_price=950,
        target_price=1120,
        opened_at=datetime.now(),
    )
    desired = TrailingEngine()._desired_stop(position, 1040)

    assert desired == 1000


def test_phase10_policy_api_exposes_lifecycle_and_effective_policy():
    create = client.post(
        "/policy/overlays",
        json={
            "overlay_id": "phase10-api-overlay",
            "key": "debate_top_n",
            "value": 4,
            "reason": "operator test",
            "proposer": "pytest",
        },
    )
    assert create.status_code == 201
    assert create.json()["status"] == "proposed"

    approve = client.post(
        "/policy/overlays/phase10-api-overlay/approve",
        json={"approver": "operator"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "active"

    effective = client.get("/policy/effective")
    assert effective.status_code == 200
    assert effective.json()["debate_top_n"] == 4

    dashboard = client.get("/dashboard/policy")
    assert dashboard.status_code == 200
    assert dashboard.json()["effective"]["debate_top_n"] == 4
