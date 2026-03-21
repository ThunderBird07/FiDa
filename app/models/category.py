from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, Enum as SAEnum
from sqlmodel import Field, SQLModel


class CategoryKind(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID | None = Field(default=None, index=True, foreign_key="user_profiles.id")
    name: str = Field(max_length=100, index=True)
    kind: CategoryKind = Field(
        default=CategoryKind.EXPENSE,
        sa_column=Column(
            SAEnum(
                CategoryKind,
                name="categorykind",
                values_callable=lambda enum_cls: [item.value for item in enum_cls],
            ),
            nullable=False,
            index=True,
        ),
    )
    encrypted_blob: str | None = Field(default=None)
    encryption_nonce: str | None = Field(default=None, max_length=255)
    encryption_version: int = Field(default=1)
    is_default: bool = Field(default=False)
