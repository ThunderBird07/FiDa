"""add country to user_profiles

Revision ID: 20260321_0004
Revises: 20260321_0003
Create Date: 2026-03-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260321_0004"
down_revision: Union[str, None] = "20260321_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("country", sa.String(length=2), nullable=False, server_default="US"),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "country")
