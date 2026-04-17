"""phase3 broker tag columns

Revision ID: 20260417_0002
Revises: 20260417_0001
Create Date: 2026-04-17 22:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0002"
down_revision = "20260417_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_intents", sa.Column("broker_tag", sa.String(length=32), nullable=True))
    op.add_column("broker_orders", sa.Column("broker_tag", sa.String(length=32), nullable=True))
    op.create_index("ix_broker_orders_broker_tag", "broker_orders", ["broker_tag"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_broker_orders_broker_tag", table_name="broker_orders")
    op.drop_column("broker_orders", "broker_tag")
    op.drop_column("order_intents", "broker_tag")
