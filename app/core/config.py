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

    # PyTrends is the highest-weighted data source (Demand dimension, Cap. 5)
    # and Google Trends rate-limits aggressively — this must retry far more
    # persistently than a generic API client before giving up on a gap.
    # Worst case (all attempts hit the max wait): ~25 minutes for one
    # keyword/country/period. Bounded, not infinite, on purpose: an
    # unbounded retry inside a FastAPI request would hang forever if Google
    # ever hard-blocks this IP, and marketmind-core's BackgroundTasks-based
    # /analyze (no worker/queue yet) has no way to resume a stuck request.
    trends_rate_limit_max_attempts: int = 12
    trends_rate_limit_initial_wait_seconds: float = 15.0
    trends_rate_limit_max_wait_seconds: float = 180.0
    trends_rate_limit_jitter_seconds: float = 10.0

    # Fallback (2026-07-08): DataForSEO's Google Trends Explore endpoint,
    # used only after the retries above are exhausted. Empty
    # login/password means the fallback is simply disabled — PyTrends
    # errors propagate exactly as before this was added. Sandbox defaults
    # to on (mock data, never billed) so the integration can be exercised
    # end-to-end before spending real credit; see
    # app/clients/dataforseo_client.py and scripts/verify_dataforseo_locations.py.
    dataforseo_login: str = ""
    dataforseo_password: str = ""
    dataforseo_use_sandbox: bool = True

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
