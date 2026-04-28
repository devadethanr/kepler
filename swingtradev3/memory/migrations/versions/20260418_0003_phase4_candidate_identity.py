"""phase4 candidate identity and linkage

Revision ID: 20260418_0003
Revises: 20260417_0002
Create Date: 2026-04-18 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260418_0003"
down_revision = "20260417_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("approvals") as batch_op:
        batch_op.drop_constraint("approvals_ticker_key", type_="unique")
        batch_op.add_column(sa.Column("entry_intent_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("order_intent_id", sa.String(length=128), nullable=True))
    op.create_index("ix_approvals_entry_intent_id", "approvals", ["entry_intent_id"], unique=False)
    op.create_index("ix_approvals_order_intent_id", "approvals", ["order_intent_id"], unique=False)

    with op.batch_alter_table("entry_intents") as batch_op:
        batch_op.add_column(sa.Column("approval_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("order_intent_id", sa.String(length=128), nullable=True))
    op.create_index("ix_entry_intents_approval_id", "entry_intents", ["approval_id"], unique=False)
    op.create_index("ix_entry_intents_order_intent_id", "entry_intents", ["order_intent_id"], unique=False)

    with op.batch_alter_table("order_intents") as batch_op:
        batch_op.add_column(sa.Column("approval_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("entry_intent_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("broker_order_id", sa.String(length=128), nullable=True))
    op.create_index("ix_order_intents_approval_id", "order_intents", ["approval_id"], unique=False)
    op.create_index("ix_order_intents_entry_intent_id", "order_intents", ["entry_intent_id"], unique=False)
    op.create_index("ix_order_intents_broker_order_id", "order_intents", ["broker_order_id"], unique=False)

    with op.batch_alter_table("broker_orders") as batch_op:
        batch_op.add_column(sa.Column("order_intent_id", sa.String(length=128), nullable=True))
    op.create_index("ix_broker_orders_order_intent_id", "broker_orders", ["order_intent_id"], unique=False)

    with op.batch_alter_table("broker_fills") as batch_op:
        batch_op.add_column(sa.Column("order_intent_id", sa.String(length=128), nullable=True))
    op.create_index("ix_broker_fills_order_intent_id", "broker_fills", ["order_intent_id"], unique=False)

    op.execute(
        """
        UPDATE approvals
        SET entry_intent_id = payload->>'entry_intent_id',
            order_intent_id = payload->>'order_intent_id'
        """
    )
    op.execute(
        """
        UPDATE entry_intents
        SET approval_id = payload->>'approval_id',
            order_intent_id = payload->>'order_intent_id'
        """
    )
    op.execute(
        """
        UPDATE order_intents
        SET approval_id = payload->>'approval_id',
            entry_intent_id = payload->>'entry_intent_id',
            broker_order_id = payload->>'broker_order_id'
        """
    )
    op.execute(
        """
        UPDATE broker_orders
        SET order_intent_id = payload->>'order_intent_id'
        """
    )
    op.execute(
        """
        UPDATE broker_fills
        SET order_intent_id = payload->>'order_intent_id'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_broker_fills_order_intent_id", table_name="broker_fills")
    with op.batch_alter_table("broker_fills") as batch_op:
        batch_op.drop_column("order_intent_id")

    op.drop_index("ix_broker_orders_order_intent_id", table_name="broker_orders")
    with op.batch_alter_table("broker_orders") as batch_op:
        batch_op.drop_column("order_intent_id")

    op.drop_index("ix_order_intents_broker_order_id", table_name="order_intents")
    op.drop_index("ix_order_intents_entry_intent_id", table_name="order_intents")
    op.drop_index("ix_order_intents_approval_id", table_name="order_intents")
    with op.batch_alter_table("order_intents") as batch_op:
        batch_op.drop_column("broker_order_id")
        batch_op.drop_column("entry_intent_id")
        batch_op.drop_column("approval_id")

    op.drop_index("ix_entry_intents_order_intent_id", table_name="entry_intents")
    op.drop_index("ix_entry_intents_approval_id", table_name="entry_intents")
    with op.batch_alter_table("entry_intents") as batch_op:
        batch_op.drop_column("order_intent_id")
        batch_op.drop_column("approval_id")

    op.drop_index("ix_approvals_order_intent_id", table_name="approvals")
    op.drop_index("ix_approvals_entry_intent_id", table_name="approvals")
    with op.batch_alter_table("approvals") as batch_op:
        batch_op.drop_column("order_intent_id")
        batch_op.drop_column("entry_intent_id")
        batch_op.create_unique_constraint("approvals_ticker_key", ["ticker"])
