from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.transaction import TransactionType


class TransactionCreate(BaseModel):
    account_id: int
    category_id: int | None = None
    type: TransactionType = TransactionType.EXPENSE
    amount: Decimal = Field(gt=0)
    occurred_at: datetime | None = None
    note: str | None = Field(default=None, max_length=255)
    encrypted_blob: str | None = None
    encryption_nonce: str | None = Field(default=None, max_length=255)
    encryption_version: int = Field(default=1, ge=1)


class TransactionUpdate(BaseModel):
    account_id: int | None = None
    category_id: int | None = None
    type: TransactionType | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    occurred_at: datetime | None = None
    note: str | None = Field(default=None, max_length=255)
    encrypted_blob: str | None = None
    encryption_nonce: str | None = Field(default=None, max_length=255)
    encryption_version: int | None = Field(default=None, ge=1)


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID
    account_id: int
    category_id: int | None
    type: TransactionType
    amount: Decimal
    occurred_at: datetime
    note: str | None
    encrypted_blob: str | None
    encryption_nonce: str | None
    encryption_version: int
    created_at: datetime
