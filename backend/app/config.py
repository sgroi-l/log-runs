from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    strava_client_id: str
    strava_client_secret: str
    secret_key: str
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
