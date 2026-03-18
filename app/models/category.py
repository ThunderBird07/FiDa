from __future__ import annotations

from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class CategoryKind(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID | None = Field(default=None, index=True, foreign_key="user_profiles.id")
    name: str = Field(max_length=100, index=True)
    kind: CategoryKind = Field(default=CategoryKind.EXPENSE, index=True)
    is_default: bool = Field(default=False)
