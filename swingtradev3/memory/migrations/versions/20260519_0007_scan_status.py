"""scan_runs table for Postgres-backed scan tracking

Revision ID: 20260519_0007
Revises: 20260517_0006
Create Date: 2026-05-19 09:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260519_0007"
down_revision = "20260517_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_runs",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_scan_runs_status", "scan_runs", ["status"])
    op.create_index("ix_scan_runs_started_at", "scan_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_scan_runs_started_at", table_name="scan_runs")
    op.drop_index("ix_scan_runs_status", table_name="scan_runs")
    op.drop_table("scan_runs")