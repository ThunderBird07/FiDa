"""add profile encryption key material

Revision ID: 20260321_0002
Revises: 20260318_0001
Create Date: 2026-03-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260321_0002"
down_revision: Union[str, None] = "20260318_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("encryption_salt", sa.String(length=255), nullable=True))
    op.add_column("user_profiles", sa.Column("wrapped_dek", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("wrapped_dek_nonce", sa.String(length=255), nullable=True))
    op.add_column(
        "user_profiles",
        sa.Column("encryption_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("user_profiles", "encryption_version", server_default=None)


def downgrade() -> None:
    op.drop_column("user_profiles", "encryption_version")
    op.drop_column("user_profiles", "wrapped_dek_nonce")
    op.drop_column("user_profiles", "wrapped_dek")
    op.drop_column("user_profiles", "encryption_salt")
