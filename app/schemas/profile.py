from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    encryption_salt: str | None
    wrapped_dek: str | None
    wrapped_dek_nonce: str | None
    encryption_version: int = 1
    country: str
    currency: str
    timezone: str
    is_active: bool


class UserProfileUpdate(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    encryption_salt: str | None = Field(default=None, max_length=255)
    wrapped_dek: str | None = None
    wrapped_dek_nonce: str | None = Field(default=None, max_length=255)
    encryption_version: int | None = Field(default=None, ge=1)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
