from uuid import UUID
from sqlmodel import SQLModel, Field


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"

    id: UUID = Field(primary_key=True)  # Supabase auth.users.id
    email: str = Field(index=True, unique=True)
    full_name: str | None = None
    encryption_salt: str | None = Field(default=None, max_length=255)
    wrapped_dek: str | None = Field(default=None)
    wrapped_dek_nonce: str | None = Field(default=None, max_length=255)
    encryption_version: int = 1
    country: str = Field(default="US", max_length=2)
    currency: str = "USD"
    timezone: str = "UTC"
    is_active: bool = True