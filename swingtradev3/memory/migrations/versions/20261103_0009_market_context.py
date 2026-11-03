"""Add immutable market context observations without changing existing rows.

Revision ID: 20261103_0009
Revises: 20261102_0008
"""

import sqlalchemy as sa
from alembic import op

revision = "20261103_0009"
down_revision = "20261102_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_context_observations",
        sa.Column("snapshot_id", sa.String(64), primary_key=True),
        sa.Column("scope", sa.String(32), nullable=False, index=True),
        sa.Column("provider", sa.String(128), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("payload", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("market_context_observations")
