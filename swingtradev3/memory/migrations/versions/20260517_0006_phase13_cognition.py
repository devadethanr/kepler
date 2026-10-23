"""phase 13 cognition audit tables

Revision ID: 20260517_0006
Revises: 20260515_0005
Create Date: 2026-05-17 09:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260517_0006"
down_revision = "20260515_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cognition_runs",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False, server_default="phase_13"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="started"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_cognition_runs_phase", "cognition_runs", ["phase"])
    op.create_index("ix_cognition_runs_status", "cognition_runs", ["status"])

    op.create_table(
        "cognition_reports",
        sa.Column("report_id", sa.String(length=160), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=True),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False, server_default="v1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("report_id"),
    )
    op.create_index("ix_cognition_reports_run_id", "cognition_reports", ["run_id"])
    op.create_index("ix_cognition_reports_ticker", "cognition_reports", ["ticker"])
    op.create_index("ix_cognition_reports_agent_name", "cognition_reports", ["agent_name"])
    op.create_index("ix_cognition_reports_status", "cognition_reports", ["status"])

    op.create_table(
        "session_execution_plans",
        sa.Column("plan_id", sa.String(length=128), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("plan_id"),
    )
    op.create_index(
        "ix_session_execution_plans_trading_date",
        "session_execution_plans",
        ["trading_date"],
    )
    op.create_index("ix_session_execution_plans_status", "session_execution_plans", ["status"])


def downgrade() -> None:
    op.drop_index("ix_session_execution_plans_status", table_name="session_execution_plans")
    op.drop_index("ix_session_execution_plans_trading_date", table_name="session_execution_plans")
    op.drop_table("session_execution_plans")

    op.drop_index("ix_cognition_reports_status", table_name="cognition_reports")
    op.drop_index("ix_cognition_reports_agent_name", table_name="cognition_reports")
    op.drop_index("ix_cognition_reports_ticker", table_name="cognition_reports")
    op.drop_index("ix_cognition_reports_run_id", table_name="cognition_reports")
    op.drop_table("cognition_reports")

    op.drop_index("ix_cognition_runs_status", table_name="cognition_runs")
    op.drop_index("ix_cognition_runs_phase", table_name="cognition_runs")
    op.drop_table("cognition_runs")

