"""Store the Google profile image URL for the workspace avatar."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_user_avatar"
down_revision: Union[str, Sequence[str], None] = "0003_google_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
