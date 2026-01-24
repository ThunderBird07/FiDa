from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "dev"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/fida"
    SECRET_KEY: str = "change-me"

    class Config:
        env_file = ".env"
    
settings = Settings()