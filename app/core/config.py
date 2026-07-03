from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "marketmind-pytrends"
    app_env: str = "local"
    app_port: int = 8000

    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "marketmind_pytrends"
    database_user: str = "marketmind"
    database_password: str = "marketmind_password"

    default_hl: str = "en-US"
    default_tz: int = 0
    default_timeframe: str = "today 12-m"
    default_timeout: int = 30
    default_retries: int = 3
    default_backoff: int = 2

    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


settings = Settings()
