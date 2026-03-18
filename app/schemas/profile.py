from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    currency: str
    timezone: str
    is_active: bool


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=100)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
