"""initial schema

Revision ID: 20260318_0001
Revises: 
Create Date: 2026-03-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260318_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


account_type = postgresql.ENUM(
    "cash",
    "bank",
    "savings",
    "credit",
    "investment",
    name="accounttype",
    create_type=False,
)
category_kind = postgresql.ENUM(
    "income",
    "expense",
    name="categorykind",
    create_type=False,
)
transaction_type = postgresql.ENUM(
    "income",
    "expense",
    "transfer",
    name="transactiontype",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    account_type.create(bind, checkfirst=True)
    category_kind.create(bind, checkfirst=True)
    transaction_type.create(bind, checkfirst=True)

    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_profiles_email"), "user_profiles", ["email"], unique=True)

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", account_type, nullable=False),
        sa.Column("balance", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounts_type"), "accounts", ["type"], unique=False)
    op.create_index(op.f("ix_accounts_user_id"), "accounts", ["user_id"], unique=False)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kind", category_kind, nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categories_kind"), "categories", ["kind"], unique=False)
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=False)
    op.create_index(op.f("ix_categories_user_id"), "categories", ["user_id"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("type", transaction_type, nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transactions_account_id"), "transactions", ["account_id"], unique=False)
    op.create_index(op.f("ix_transactions_category_id"), "transactions", ["category_id"], unique=False)
    op.create_index(op.f("ix_transactions_created_at"), "transactions", ["created_at"], unique=False)
    op.create_index(op.f("ix_transactions_occurred_at"), "transactions", ["occurred_at"], unique=False)
    op.create_index(op.f("ix_transactions_type"), "transactions", ["type"], unique=False)
    op.create_index(op.f("ix_transactions_user_id"), "transactions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_user_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_type"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_occurred_at"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_created_at"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_category_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_account_id"), table_name="transactions")
    op.drop_table("transactions")

    op.drop_index(op.f("ix_categories_user_id"), table_name="categories")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_kind"), table_name="categories")
    op.drop_table("categories")

    op.drop_index(op.f("ix_accounts_user_id"), table_name="accounts")
    op.drop_index(op.f("ix_accounts_type"), table_name="accounts")
    op.drop_table("accounts")

    op.drop_index(op.f("ix_user_profiles_email"), table_name="user_profiles")
    op.drop_table("user_profiles")

    bind = op.get_bind()
    transaction_type.drop(bind, checkfirst=True)
    category_kind.drop(bind, checkfirst=True)
    account_type.drop(bind, checkfirst=True)
