"""Integration-test harness: real FastAPI app + real Postgres, mocked third parties.

- Database: a dedicated `<dev db>_test` database on the same local docker-compose Postgres,
  created on demand and migrated with the real Alembic migrations. Tables are truncated
  around every test, so tests never see each other's data and the dev data is never touched.
- Auth: real JWT verification code runs; tests mint RS256 tokens with a throwaway key and the
  JWKS client is swapped for one that serves that key (no Clerk network call).
- External services (Open Library, TMDB, Clerk's profile API) are mocked, like the unit tests.
"""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.db import get_db
from app.main import app
from app.schemas.work import WorkCreate
from app.services.open_library_service import OpenLibraryService
from app.services.tmdb_service import TMDBService
from app.services.user_service import UserService

REPO_ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- database

@pytest.fixture(scope="session")
def test_database_url() -> str:
    dev_url = make_url(settings.database_url)
    name = dev_url.database if dev_url.database.endswith("_test") else f"{dev_url.database}_test"
    assert name.endswith("_test")  # hard guard: we TRUNCATE this database between tests
    test_url = dev_url.set(database=name)

    async def ensure_database() -> None:
        admin = create_async_engine(dev_url.set(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool)
        try:
            async with admin.connect() as conn:
                exists = (await conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name})).scalar()
                if not exists:
                    await conn.execute(text(f'CREATE DATABASE "{name}"'))
        finally:
            await admin.dispose()

    try:
        asyncio.run(ensure_database())
    except Exception as exc:  # noqa: BLE001 - any connectivity failure means "no DB here"
        pytest.skip(f"Postgres not reachable for integration tests (run `docker compose up -d db`): {exc!r}")

    url_string = test_url.render_as_string(hide_password=False)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env={**os.environ, "DATABASE_URL": url_string},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic upgrade failed on the test DB:\n{result.stderr}"
    return url_string


async def _truncate_all(engine) -> None:
    async with engine.begin() as conn:
        names = (
            await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'")
            )
        ).scalars().all()
        if names:
            await conn.execute(text("TRUNCATE " + ", ".join(f'"{n}"' for n in names) + " CASCADE"))


@pytest.fixture
async def engine(test_database_url):
    # NullPool: no connection outlives the (per-test) event loop it was created on.
    eng = create_async_engine(test_database_url, poolclass=NullPool)
    await _truncate_all(eng)
    yield eng
    await _truncate_all(eng)
    await eng.dispose()


@pytest.fixture
def session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


# --------------------------------------------------------------------------- auth

@pytest.fixture(scope="session")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def make_token(signing_key):
    def _make(sub: str | None = "user_alice", *, issuer: str | None = None, expires_in: int = 3600, key=None) -> str:
        now = int(time.time())
        payload = {"iss": issuer or settings.clerk_issuer, "iat": now, "exp": now + expires_in}
        if sub is not None:
            payload["sub"] = sub
        return jwt.encode(payload, key or signing_key, algorithm="RS256", headers={"kid": "test-key"})

    return _make


@pytest.fixture
def auth_headers(make_token):
    def _headers(sub: str = "user_alice") -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(sub)}"}

    return _headers


# --------------------------------------------------------------------------- external services

BOOK_CATALOG = [
    WorkCreate(
        medium="BOOK", title="Dune", creator="Frank Herbert", external_id="OL-DUNE",
        synopsis="Politics and prophecy on a desert planet.", subjects=["Science fiction", "Politics"],
    ),
]
FILM_CATALOG = [
    WorkCreate(
        medium="FILM", title="Dune", creator="Denis Villeneuve", external_id="TMDB-DUNE",
        synopsis="A noble family takes over Arrakis.", subjects=["Science Fiction", "Adventure"],
    ),
    WorkCreate(
        medium="FILM", title="Alien", creator="Ridley Scott", external_id="TMDB-ALIEN",
        synopsis="A crew meets something in the dark.", subjects=["Horror", "Science Fiction"],
    ),
    WorkCreate(
        medium="FILM", title="Pride and Prejudice", creator="Joe Wright", external_id="TMDB-PP",
        synopsis="Manners and misjudgement.", subjects=["Romance", "Drama"],
    ),
]


@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    """Fake Open Library / TMDB / Clerk profile lookups: substring match on a fixed catalog."""

    def fake_search(catalog):
        async def search(self, query: str) -> list[WorkCreate]:
            return [w.model_copy(deep=True) for w in catalog if query.lower() in w.title.lower()]

        return search

    async def fake_profile(self, clerk_id: str) -> tuple[str, str]:
        return f"{clerk_id}@test.dev", f"Test {clerk_id}"

    monkeypatch.setattr(OpenLibraryService, "search", fake_search(BOOK_CATALOG))
    monkeypatch.setattr(TMDBService, "search", fake_search(FILM_CATALOG))
    monkeypatch.setattr(UserService, "_fetch_clerk_profile", fake_profile)


# --------------------------------------------------------------------------- HTTP client

@pytest.fixture
async def client(session_maker, signing_key, monkeypatch):
    async def override_get_db():
        async with session_maker() as session:
            yield session

    class FakeJWKSClient:
        # Like PyJWKClient: rejects tokens that don't even parse, otherwise serves our test key.
        def get_signing_key_from_jwt(self, token: str):
            jwt.get_unverified_header(token)
            return SimpleNamespace(key=signing_key.public_key())

    monkeypatch.setattr("app.core.auth._jwks_client", FakeJWKSClient())
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.clear()
