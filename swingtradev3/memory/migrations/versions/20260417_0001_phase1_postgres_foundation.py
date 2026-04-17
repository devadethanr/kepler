"""Phase 1 Postgres foundation."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_state",
        sa.Column("account_key", sa.String(length=32), primary_key=True),
        sa.Column("cash_inr", sa.Float(), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unrealized_pnl", sa.Float(), nullable=False, server_default="0"),
        sa.Column("drawdown_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("weekly_loss_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("consecutive_losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "positions",
        sa.Column("position_id", sa.String(length=128), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("stop_price", sa.Float(), nullable=False),
        sa.Column("target_price", sa.Float(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("ticker"),
    )
    op.create_index("ix_positions_ticker", "positions", ["ticker"], unique=False)
    op.create_table(
        "approvals",
        sa.Column("approval_id", sa.String(length=128), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("approved", sa.Boolean(), nullable=True),
        sa.Column("execution_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("execution_request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at_effective", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("ticker"),
    )
    op.create_index("ix_approvals_ticker", "approvals", ["ticker"], unique=False)
    op.create_table(
        "trades",
        sa.Column("trade_id", sa.String(length=128), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("exit_price", sa.Float(), nullable=False),
        sa.Column("opened_at_effective", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at_effective", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pnl_abs", sa.Float(), nullable=False),
        sa.Column("pnl_pct", sa.Float(), nullable=False),
        sa.Column("exit_reason", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_trades_ticker", "trades", ["ticker"], unique=False)
    op.create_table(
        "auth_sessions",
        sa.Column("session_key", sa.String(length=64), primary_key=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("public_token", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_auth_sessions_provider", "auth_sessions", ["provider"], unique=False)
    op.create_table(
        "execution_events",
        sa.Column("event_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_execution_events_event_type", "execution_events", ["event_type"], unique=False)
    op.create_index("ix_execution_events_entity_type", "execution_events", ["entity_type"], unique=False)
    op.create_index("ix_execution_events_entity_id", "execution_events", ["entity_id"], unique=False)
    op.create_table(
        "entry_intents",
        sa.Column("intent_id", sa.String(length=128), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="proposed"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_entry_intents_ticker", "entry_intents", ["ticker"], unique=False)
    op.create_table(
        "order_intents",
        sa.Column("order_intent_id", sa.String(length=128), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="proposed"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_order_intents_ticker", "order_intents", ["ticker"], unique=False)
    op.create_table(
        "broker_orders",
        sa.Column("broker_order_id", sa.String(length=128), primary_key=True),
        sa.Column("exchange_order_id", sa.String(length=128), nullable=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_broker_orders_ticker", "broker_orders", ["ticker"], unique=False)
    op.create_table(
        "broker_fills",
        sa.Column("fill_id", sa.String(length=128), primary_key=True),
        sa.Column("broker_order_id", sa.String(length=128), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("fill_price", sa.Float(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_broker_fills_broker_order_id", "broker_fills", ["broker_order_id"], unique=False)
    op.create_index("ix_broker_fills_ticker", "broker_fills", ["ticker"], unique=False)
    op.create_table(
        "protective_triggers",
        sa.Column("protective_trigger_id", sa.String(length=128), primary_key=True),
        sa.Column("position_id", sa.String(length=128), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending_arm"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_protective_triggers_position_id", "protective_triggers", ["position_id"], unique=False)
    op.create_index("ix_protective_triggers_ticker", "protective_triggers", ["ticker"], unique=False)
    op.create_table(
        "policy_overlays",
        sa.Column("overlay_id", sa.String(length=128), primary_key=True),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="proposed"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_policy_overlays_key", "policy_overlays", ["key"], unique=False)
    op.create_table(
        "reconciliation_runs",
        sa.Column("reconciliation_run_id", sa.String(length=128), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="started"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "failure_incidents",
        sa.Column("incident_id", sa.String(length=128), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="warning"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_table(
        "operator_controls",
        sa.Column("control_key", sa.String(length=128), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("operator_controls")
    op.drop_table("failure_incidents")
    op.drop_table("reconciliation_runs")
    op.drop_index("ix_policy_overlays_key", table_name="policy_overlays")
    op.drop_table("policy_overlays")
    op.drop_index("ix_protective_triggers_ticker", table_name="protective_triggers")
    op.drop_index("ix_protective_triggers_position_id", table_name="protective_triggers")
    op.drop_table("protective_triggers")
    op.drop_index("ix_broker_fills_ticker", table_name="broker_fills")
    op.drop_index("ix_broker_fills_broker_order_id", table_name="broker_fills")
    op.drop_table("broker_fills")
    op.drop_index("ix_broker_orders_ticker", table_name="broker_orders")
    op.drop_table("broker_orders")
    op.drop_index("ix_order_intents_ticker", table_name="order_intents")
    op.drop_table("order_intents")
    op.drop_index("ix_entry_intents_ticker", table_name="entry_intents")
    op.drop_table("entry_intents")
    op.drop_index("ix_execution_events_entity_id", table_name="execution_events")
    op.drop_index("ix_execution_events_entity_type", table_name="execution_events")
    op.drop_index("ix_execution_events_event_type", table_name="execution_events")
    op.drop_table("execution_events")
    op.drop_index("ix_auth_sessions_provider", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_trades_ticker", table_name="trades")
    op.drop_table("trades")
    op.drop_index("ix_approvals_ticker", table_name="approvals")
    op.drop_table("approvals")
    op.drop_index("ix_positions_ticker", table_name="positions")
    op.drop_table("positions")
    op.drop_table("account_state")
