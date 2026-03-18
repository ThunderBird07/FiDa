from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.account import AccountType


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: AccountType = AccountType.BANK
    balance: Decimal = Decimal("0.00")
    currency: str = Field(default="USD", min_length=3, max_length=3)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: AccountType | None = None
    balance: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    name: str
    type: AccountType
    balance: Decimal
    currency: str
    is_active: bool
