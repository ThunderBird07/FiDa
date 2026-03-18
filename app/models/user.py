from uuid import UUID
from sqlmodel import SQLModel, Field


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"

    id: UUID = Field(primary_key=True)  # Supabase auth.users.id
    email: str = Field(index=True, unique=True)
    full_name: str | None = None
    currency: str = "USD"
    timezone: str = "UTC"
    is_active: bool = True