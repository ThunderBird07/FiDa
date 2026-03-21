from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, Enum as SAEnum
from sqlmodel import Field, SQLModel


class AccountType(str, Enum):
    CASH = "cash"
    BANK = "bank"
    SAVINGS = "savings"
    CREDIT = "credit"
    INVESTMENT = "investment"


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(index=True, foreign_key="user_profiles.id")
    name: str = Field(max_length=100)
    type: AccountType = Field(
        default=AccountType.BANK,
        sa_column=Column(
            SAEnum(
                AccountType,
                name="accounttype",
                values_callable=lambda enum_cls: [item.value for item in enum_cls],
            ),
            nullable=False,
            index=True,
        ),
    )
    balance: Decimal = Field(default=Decimal("0.00"), decimal_places=2, max_digits=14)
    currency: str = Field(default="USD", max_length=3)
    encrypted_blob: str | None = Field(default=None)
    encryption_nonce: str | None = Field(default=None, max_length=255)
    encryption_version: int = Field(default=1)
    is_active: bool = Field(default=True)
