from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "dev"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/fida"
    MIGRATION_DATABASE_URL: str | None = None
    DIRECT_URL: str | None = None
    SECRET_KEY: str = "change-me"
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_AUDIENCE: str = "authenticated"

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def supabase_issuer(self) -> str:
        return f"{self.SUPABASE_URL.rstrip('/')}/auth/v1"

    @property
    def migration_database_url(self) -> str:
        return self.MIGRATION_DATABASE_URL or self.DATABASE_URL


settings = Settings()