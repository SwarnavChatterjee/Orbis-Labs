"""Persist query progress events for SSE replay.

Revision ID: 0002_query_events
Revises: 0001_initial
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_query_events"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "query_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("query_id", sa.Uuid(), sa.ForeignKey("queries.id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_query_events_query_id", "query_events", ["query_id"])


def downgrade() -> None:
    op.drop_index("ix_query_events_query_id", table_name="query_events")
    op.drop_table("query_events")
