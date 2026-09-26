"""Create the initial Orbis Labs schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
    )
    op.create_table(
        "queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parsed_params", postgresql.JSONB()),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("queries.id"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sources.id")),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("location", sa.Text()),
        sa.Column("stipend", postgresql.JSONB()),
        sa.Column("deadline", sa.Date()),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2)),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_queries_status", "queries", ["status"])
    op.create_index("ix_queries_project_id", "queries", ["project_id"])
    op.create_index("ix_records_query_id", "records", ["query_id"])
    op.create_index("ix_records_company_trgm", "records", ["company"], postgresql_using="gin", postgresql_ops={"company": "gin_trgm_ops"})
    op.create_index("ix_records_role_trgm", "records", ["role"], postgresql_using="gin", postgresql_ops={"role": "gin_trgm_ops"})


def downgrade() -> None:
    op.drop_table("records")
    op.drop_table("queries")
    op.drop_table("sources")
    op.drop_table("projects")
    op.drop_table("users")
