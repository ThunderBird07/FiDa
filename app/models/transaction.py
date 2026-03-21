from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, Enum as SAEnum
from sqlmodel import Field, SQLModel


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(index=True, foreign_key="user_profiles.id")
    account_id: int = Field(index=True, foreign_key="accounts.id")
    category_id: int | None = Field(default=None, index=True, foreign_key="categories.id")
    type: TransactionType = Field(
        default=TransactionType.EXPENSE,
        sa_column=Column(
            SAEnum(
                TransactionType,
                name="transactiontype",
                values_callable=lambda enum_cls: [item.value for item in enum_cls],
            ),
            nullable=False,
            index=True,
        ),
    )
    amount: Decimal = Field(decimal_places=2, max_digits=14)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    note: str | None = Field(default=None, max_length=255)
    encrypted_blob: str | None = Field(default=None)
    encryption_nonce: str | None = Field(default=None, max_length=255)
    encryption_version: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
