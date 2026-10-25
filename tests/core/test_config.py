import pytest

from app.core.config import Settings

REQUIRED = dict(
    database_url="postgresql+asyncpg://u:p@localhost/db",
    clerk_publishable_key="pk",
    clerk_secret_key="sk",
    clerk_issuer="https://example.clerk.accounts.dev",
    tmdb_api_key="tmdb",
)


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **{**REQUIRED, **overrides})


@pytest.mark.parametrize(
    "raw",
    ["postgres://u:p@host:5432/db", "postgresql://u:p@host:5432/db"],
)
def test_plain_postgres_urls_are_rewritten_to_asyncpg(raw):
    assert make_settings(database_url=raw).database_url == "postgresql+asyncpg://u:p@host:5432/db"


def test_asyncpg_url_is_left_alone():
    url = "postgresql+asyncpg://u:p@host:5432/db"
    assert make_settings(database_url=url).database_url == url


def test_postgres_vars_are_optional():
    settings = make_settings()
    assert settings.postgres_db is None
    assert settings.postgres_port is None


def test_cors_origins_default_to_empty():
    assert make_settings().cors_origin_list == []


def test_cors_origins_are_split_and_trimmed():
    settings = make_settings(cors_origins=" https://a.example.com , http://localhost:3000,, ")
    assert settings.cors_origin_list == ["https://a.example.com", "http://localhost:3000"]
