from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.category import CategoryKind


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: CategoryKind = CategoryKind.EXPENSE
    encrypted_blob: str | None = None
    encryption_nonce: str | None = Field(default=None, max_length=255)
    encryption_version: int = Field(default=1, ge=1)
    is_default: bool = False


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    kind: CategoryKind | None = None
    encrypted_blob: str | None = None
    encryption_nonce: str | None = Field(default=None, max_length=255)
    encryption_version: int | None = Field(default=None, ge=1)
    is_default: bool | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID | None
    name: str
    kind: CategoryKind
    encrypted_blob: str | None
    encryption_nonce: str | None
    encryption_version: int
    is_default: bool
