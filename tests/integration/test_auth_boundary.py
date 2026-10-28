"""Public-vs-authenticated boundary, enforced through the real dependency stack."""
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import text

pytestmark = pytest.mark.integration

_ID = uuid.uuid4()

PROTECTED = [
    ("GET", "/auth/me", None),
    ("GET", "/interactions/me", None),
    ("POST", "/interactions", {"work_id": str(_ID), "rating": 5}),
    ("POST", f"/interactions/{_ID}/tags", {"tag_name": "x", "sentiment": "POSITIVE"}),
    ("DELETE", f"/interactions/{_ID}", None),
    ("DELETE", f"/interactions/{_ID}/tags/{_ID}", None),
    ("GET", "/recommendations", None),
]

PUBLIC = [
    ("GET", "/health", 200),
    ("GET", "/works/search?q=dune", 200),
    ("GET", f"/works/{_ID}", 404),  # reachable without a token; the work just doesn't exist
    ("GET", f"/interactions/{_ID}/tags", None),  # any non-auth outcome is fine
]


def _bad_tokens(make_token):
    return {
        "garbage": "not-a-jwt",
        "expired": make_token("user_alice", expires_in=-60),
        "wrong issuer": make_token("user_alice", issuer="https://evil.example.com"),
        "signed by a different key": make_token("user_alice", key=rsa.generate_private_key(public_exponent=65537, key_size=2048)),
        "missing sub claim": make_token(None),
    }


@pytest.mark.parametrize("method,path,body", PROTECTED)
async def test_protected_routes_reject_missing_authorization(client, method, path, body):
    r = await client.request(method, path, json=body)
    assert r.status_code == 401


@pytest.mark.parametrize("method,path,body", PROTECTED)
async def test_protected_routes_reject_invalid_tokens(client, make_token, session_maker, method, path, body):
    for label, token in _bad_tokens(make_token).items():
        r = await client.request(method, path, json=body, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, f"{label}: expected 401, got {r.status_code} {r.text}"

    r = await client.request(method, path, json=body, headers={"Authorization": "Basic dXNlcjpwdw=="})
    assert r.status_code == 401, "non-bearer scheme"

    # a rejected token must never provision a local user
    async with session_maker() as db:
        assert (await db.execute(text("SELECT count(*) FROM users"))).scalar() == 0


@pytest.mark.parametrize("method,path,expected", PUBLIC)
async def test_public_routes_work_without_a_token(client, method, path, expected):
    r = await client.request(method, path)
    assert r.status_code not in (401, 403)
    if expected is not None:
        assert r.status_code == expected


async def test_valid_token_is_accepted(client, auth_headers):
    r = await client.get("/auth/me", headers=auth_headers("user_alice"))
    assert r.status_code == 200
