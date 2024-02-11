from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    pg_dsn: str = "postgres://postgres:password@localhost:5932/tracks.lat"

    session_secret_key: str = "session-secret"

    registrations_open: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TRACKSLAT_",
    )


settings = Settings()
