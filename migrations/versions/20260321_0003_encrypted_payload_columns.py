"""add encrypted payload columns to core financial tables

Revision ID: 20260321_0003
Revises: 20260321_0002
Create Date: 2026-03-21

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260321_0003"
down_revision: Union[str, None] = "20260321_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_encryption_columns(table_name: str) -> None:
    op.add_column(table_name, sa.Column("encrypted_blob", sa.Text(), nullable=True))
    op.add_column(table_name, sa.Column("encryption_nonce", sa.String(length=255), nullable=True))
    op.add_column(table_name, sa.Column("encryption_version", sa.Integer(), nullable=False, server_default="1"))
    op.alter_column(table_name, "encryption_version", server_default=None)


def _drop_encryption_columns(table_name: str) -> None:
    op.drop_column(table_name, "encryption_version")
    op.drop_column(table_name, "encryption_nonce")
    op.drop_column(table_name, "encrypted_blob")


def upgrade() -> None:
    _add_encryption_columns("accounts")
    _add_encryption_columns("categories")
    _add_encryption_columns("transactions")


def downgrade() -> None:
    _drop_encryption_columns("transactions")
    _drop_encryption_columns("categories")
    _drop_encryption_columns("accounts")
