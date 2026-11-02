"""Add immutable news source versions and observations.

Revision ID: 20261102_0008
Revises: 20260519_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20261102_0008"
down_revision = "20260519_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("news_source_versions",
        sa.Column("version_id", sa.String(64), primary_key=True),
        sa.Column("source_key", sa.String(64), nullable=False, index=True),
        sa.Column("provider", sa.String(128), nullable=False, index=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False))
    op.create_table("news_source_observations",
        sa.Column("observation_id", sa.String(32), primary_key=True),
        sa.Column("source_key", sa.String(64), nullable=False, index=True),
        sa.Column("version_id", sa.String(64), nullable=False, index=True),
        sa.Column("supersedes_version_id", sa.String(64), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, index=True))
    op.create_table("news_source_fetches",
        sa.Column("fetch_id", sa.String(32), primary_key=True),
        sa.Column("provider", sa.String(128), nullable=False, index=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("payload", sa.JSON(), nullable=False))


def downgrade() -> None:
    op.drop_table("news_source_fetches")
    op.drop_table("news_source_observations")
    op.drop_table("news_source_versions")
