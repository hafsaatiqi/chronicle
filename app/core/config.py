from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    # Only docker-compose uses these (to provision the local Postgres container);
    # the app itself connects via `database_url`, so they're optional in deployed envs.
    postgres_db: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_host: str | None = None
    postgres_port: int | None = None

    clerk_publishable_key: str
    clerk_secret_key: str
    clerk_issuer: str

    tmdb_api_key: str

    # Comma-separated list of allowed browser origins, e.g. "https://app.example.com,http://localhost:3000".
    # Empty means CORS is disabled (no cross-origin browser access).
    cors_origins: str = ""

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_driver(cls, value: str) -> str:
        # Managed Postgres providers (Railway, Heroku, Neon) hand out plain `postgres://` or
        # `postgresql://` URLs; the app is async-only and needs the asyncpg driver explicitly.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix):]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
