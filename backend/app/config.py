from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    strava_client_id: str
    strava_client_secret: str
    secret_key: str
    frontend_url: str = "http://localhost:5173"

    @field_validator("database_url")
    @classmethod
    def _normalize_postgres_scheme(cls, v: str) -> str:
        # Fly (and Heroku) inject postgres://, but SQLAlchemy 2.x requires postgresql://
        if v.startswith("postgres://"):
            return "postgresql://" + v[len("postgres://"):]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
