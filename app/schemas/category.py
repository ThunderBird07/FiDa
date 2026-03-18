from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.category import CategoryKind


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: CategoryKind = CategoryKind.EXPENSE
    is_default: bool = False


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    kind: CategoryKind | None = None
    is_default: bool | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID | None
    name: str
    kind: CategoryKind
    is_default: bool
