"""Bad input is rejected at the HTTP layer with the right status, not a 500."""
import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
async def work_id(client) -> str:
    return (await client.get("/works/search", params={"q": "dune"})).json()[0]["id"]


@pytest.fixture
async def interaction_id(client, auth_headers, work_id) -> str:
    r = await client.post("/interactions", json={"work_id": work_id, "rating": 5}, headers=auth_headers())
    return r.json()["id"]


@pytest.mark.parametrize(
    "params",
    [{}, {"q": ""}, {"q": "a"}, {"q": "dune", "medium": "GAME"}, {"q": "dune", "medium": "book"}],
    ids=["missing q", "empty q", "q too short", "unknown medium", "wrong-case medium"],
)
async def test_search_rejects_bad_query_params(client, params):
    r = await client.get("/works/search", params=params)
    assert r.status_code == 422


async def test_work_lookup_rejects_non_uuid(client):
    assert (await client.get("/works/not-a-uuid")).status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"rating": 5},
        {"work_id": "not-a-uuid", "rating": 5},
        {"work_id": "{work_id}", "rating": 0},
        {"work_id": "{work_id}", "rating": 6},
        {"work_id": "{work_id}", "rating": "five"},
        {"work_id": "{work_id}", "status": "NOT_A_STATUS"},
        {"work_id": "{work_id}", "status": "IN_PROGRESS", "rating": 4},
        {"work_id": "{work_id}", "status": "WANT_TO", "rating": 4},
    ],
    ids=[
        "empty body", "missing work_id", "non-uuid work_id", "rating 0", "rating 6", "rating not a number",
        "unknown status", "rating on IN_PROGRESS", "rating on WANT_TO",
    ],
)
async def test_log_interaction_rejects_bad_bodies(client, auth_headers, work_id, body):
    body = {k: (work_id if v == "{work_id}" else v) for k, v in body.items()}
    r = await client.post("/interactions", json=body, headers=auth_headers())
    assert r.status_code == 422, r.text


async def test_log_interaction_for_unknown_work_is_404(client, auth_headers):
    r = await client.post("/interactions", json={"work_id": str(uuid.uuid4()), "rating": 5}, headers=auth_headers())
    assert r.status_code == 404


async def test_shelf_rejects_unknown_status_filter(client, auth_headers):
    r = await client.get("/interactions/me", params={"status": "BOGUS"}, headers=auth_headers())
    assert r.status_code == 422


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"tag_name": "slow burn"},
        {"sentiment": "POSITIVE"},
        {"tag_name": "slow burn", "sentiment": "MEH"},
        {"tag_name": "slow burn", "sentiment": "positive"},
        {"tag_name": "slow burn", "sentiment": "POSITIVE", "category": "NOT_A_CATEGORY"},
    ],
    ids=["empty", "missing sentiment", "missing tag_name", "unknown sentiment", "wrong-case sentiment", "unknown category"],
)
async def test_tagging_rejects_bad_bodies(client, auth_headers, interaction_id, body):
    r = await client.post(f"/interactions/{interaction_id}/tags", json=body, headers=auth_headers())
    assert r.status_code == 422, r.text


async def test_tagging_rejects_non_uuid_interaction_id(client, auth_headers):
    r = await client.post(
        "/interactions/nope/tags", json={"tag_name": "x", "sentiment": "POSITIVE"}, headers=auth_headers()
    )
    assert r.status_code == 422


@pytest.mark.parametrize("limit", ["0", "-1", "51", "abc"])
async def test_recommendations_reject_bad_limit(client, auth_headers, limit):
    r = await client.get("/recommendations", params={"limit": limit}, headers=auth_headers())
    assert r.status_code == 422


async def test_validation_failures_persist_nothing(client, auth_headers, work_id, session_maker):
    from sqlalchemy import text

    await client.post("/interactions", json={"work_id": work_id, "rating": 99}, headers=auth_headers())
    await client.post("/interactions", json={"work_id": work_id, "status": "IN_PROGRESS", "rating": 4}, headers=auth_headers())
    async with session_maker() as db:
        assert (await db.execute(text("SELECT count(*) FROM user_interactions"))).scalar() == 0
