"""Store verified Google identity metadata."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_google_identity"
down_revision: Union[str, Sequence[str], None] = "0002_query_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_subject", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("display_name", sa.Text(), nullable=True))
    op.create_index("ix_users_google_subject", "users", ["google_subject"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_google_subject", table_name="users")
    op.drop_column("users", "display_name")
    op.drop_column("users", "google_subject")
