from urllib.parse import quote

from pydantic_settings import BaseSettings

from app.db.ssl_config import sslmode_query_suffix


class Settings(BaseSettings):
    app_name: str = "marketmind-pytrends"
    app_env: str = "local"

    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "marketmind_pytrends"
    database_user: str = "marketmind"
    database_password: str = "marketmind_password"

    # TLS for the Postgres connection. "disable" keeps local docker-compose
    # working unchanged; Azure Database for PostgreSQL Flexible Server needs at
    # least "require" because it refuses plaintext connections
    # (`require_secure_transport = ON`). See app/db/ssl_config.py.
    database_ssl_mode: str = "disable"

    # The language a request is made in when the caller does not say.
    default_hl: str = "en-US"

    # How the DataForSEO client insists: `default_retries` attempts, sleeping
    # `default_backoff * attempt` seconds between them (linear), on 5xx, 429,
    # timeouts, network errors and 5xxxx task codes. Worst case with the
    # defaults: 3 attempts and 2 + 4 = 6 seconds of waiting. Client-side errors
    # (4xx, 4xxxx task codes) are never retried. See
    # app/clients/dataforseo_client.py::_run_with_retry.
    default_retries: int = 3
    default_backoff: int = 2

    # DataForSEO Google Ads credentials (login and API password, from the
    # dashboard — the API password is not the account password). Sandbox is the
    # default IN CODE so a fresh checkout never bills anyone: same auth, same
    # shapes, mock data. Every deployment sets it to false; the collector is
    # useless on mock data. See app/clients/dataforseo_client.py.
    dataforseo_login: str = ""
    dataforseo_password: str = ""
    dataforseo_use_sandbox: bool = True

    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.database_user}:{quote(self.database_password, safe='')}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def database_url_sync(self) -> str:
        # Alembic runs through psycopg2, which reads `sslmode` straight off
        # the DSN. The async engine cannot — it gets an SSLContext instead,
        # built from the same setting in app/db/ssl_config.py.
        return (
            f"postgresql://{self.database_user}:{quote(self.database_password, safe='')}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
            f"{sslmode_query_suffix(self.database_ssl_mode)}"
        )


settings = Settings()
