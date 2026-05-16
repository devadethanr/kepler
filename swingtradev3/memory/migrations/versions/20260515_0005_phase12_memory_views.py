"""phase 12 curated memory views

Revision ID: 20260515_0005
Revises: 20260506_0004
Create Date: 2026-05-15 10:30:00.000000
"""

from __future__ import annotations

from alembic import op


revision = "20260515_0005"
down_revision = "20260506_0004"
branch_labels = None
depends_on = None


VIEWS: dict[str, str] = {
    "portfolio_risk_view": """
        CREATE OR REPLACE VIEW portfolio_risk_view AS
        SELECT
            a.account_key,
            a.cash_inr,
            a.realized_pnl,
            a.unrealized_pnl,
            (a.realized_pnl + a.unrealized_pnl) AS total_pnl,
            a.drawdown_pct,
            a.weekly_loss_pct,
            a.consecutive_losses,
            COALESCE(p.open_positions_count, 0) AS open_positions_count,
            COALESCE(p.open_exposure_inr, 0.0) AS open_exposure_inr,
            a.updated_at
        FROM account_state a
        LEFT JOIN (
            SELECT
                COUNT(*) AS open_positions_count,
                SUM(quantity * entry_price) AS open_exposure_inr
            FROM positions
            WHERE state IN ('open', 'closing', 'pending_entry')
        ) p ON TRUE
    """,
    "open_positions_view": """
        CREATE OR REPLACE VIEW open_positions_view AS
        SELECT
            position_id,
            ticker,
            state,
            quantity,
            entry_price,
            stop_price,
            target_price,
            opened_at,
            payload ->> 'sector' AS sector,
            payload ->> 'setup_type' AS setup_type,
            payload ->> 'skill_version' AS skill_version,
            payload ->> 'research_date' AS research_date,
            payload,
            updated_at
        FROM positions
        WHERE state IN ('open', 'closing', 'pending_entry')
    """,
    "execution_incidents_view": """
        CREATE OR REPLACE VIEW execution_incidents_view AS
        SELECT
            incident_id,
            status,
            severity,
            payload ->> 'reason' AS reason,
            payload ->> 'ticker' AS ticker,
            payload,
            created_at,
            updated_at
        FROM failure_incidents
        ORDER BY
            CASE WHEN status = 'open' THEN 0 ELSE 1 END,
            updated_at DESC
    """,
    "policy_effective_view": """
        CREATE OR REPLACE VIEW policy_effective_view AS
        SELECT
            overlay_id,
            key,
            value,
            status,
            payload ->> 'reason' AS reason,
            payload ->> 'proposer' AS proposer,
            payload ->> 'approver' AS approver,
            payload ->> 'expires_at' AS expires_at,
            (
                status IN ('active', 'approved')
                AND (
                    payload ->> 'expires_at' IS NULL
                    OR payload ->> 'expires_at' = ''
                    OR (payload ->> 'expires_at')::timestamptz > now()
                )
            ) AS is_effective_candidate,
            payload,
            created_at,
            updated_at
        FROM policy_overlays
        ORDER BY updated_at DESC
    """,
    "session_readiness_view": """
        CREATE OR REPLACE VIEW session_readiness_view AS
        SELECT
            now() AS as_of,
            COALESCE((trading.value ->> 'enabled')::boolean, false) AS trading_enabled,
            COALESCE((entries.value ->> 'enabled')::boolean, false) AS new_entries_enabled,
            COALESCE((exit_only.value ->> 'enabled')::boolean, false) AS exit_only_mode,
            COALESCE((block_entries.value ->> 'active')::boolean, false) AS block_new_entries,
            block_entries.value -> 'reasons' AS block_reasons,
            worker.value AS worker_status,
            reconciliation.value AS reconciliation_status
        FROM (SELECT 1) seed
        LEFT JOIN operator_controls trading ON trading.control_key = 'trading_enabled'
        LEFT JOIN operator_controls entries ON entries.control_key = 'new_entries_enabled'
        LEFT JOIN operator_controls exit_only ON exit_only.control_key = 'exit_only_mode'
        LEFT JOIN operator_controls block_entries ON block_entries.control_key = 'block_new_entries'
        LEFT JOIN operator_controls worker ON worker.control_key = 'worker_status'
        LEFT JOIN operator_controls reconciliation
            ON reconciliation.control_key = 'reconciliation_status'
    """,
    "recent_trades_view": """
        CREATE OR REPLACE VIEW recent_trades_view AS
        SELECT
            trade_id,
            ticker,
            quantity,
            entry_price,
            exit_price,
            opened_at_effective,
            closed_at_effective,
            pnl_abs,
            pnl_pct,
            exit_reason,
            payload ->> 'setup_type' AS setup_type,
            payload ->> 'skill_version' AS skill_version,
            payload,
            updated_at
        FROM trades
        ORDER BY closed_at_effective DESC, trade_id ASC
    """,
    "reconciliation_readiness_view": """
        CREATE OR REPLACE VIEW reconciliation_readiness_view AS
        SELECT
            reconciliation_run_id,
            status,
            payload,
            created_at,
            updated_at
        FROM reconciliation_runs
        ORDER BY updated_at DESC
    """,
    "operator_controls_view": """
        CREATE OR REPLACE VIEW operator_controls_view AS
        SELECT
            control_key,
            value,
            payload,
            created_at,
            updated_at
        FROM operator_controls
        ORDER BY control_key ASC
    """,
}


def upgrade() -> None:
    for statement in VIEWS.values():
        op.execute(statement)


def downgrade() -> None:
    for view_name in reversed(VIEWS):
        op.execute(f"DROP VIEW IF EXISTS {view_name}")
