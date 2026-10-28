"""Removing logged items/tags and paging the shelf, through the real HTTP stack."""
import uuid

import pytest

pytestmark = pytest.mark.integration


async def _log(client, headers, query, medium="BOOK", **body):
    work_id = (await client.get("/works/search", params={"q": query, "medium": medium})).json()[0]["id"]
    r = await client.post("/interactions", json={"work_id": work_id, **body}, headers=headers)
    assert r.status_code == 200
    return r.json()


async def test_delete_interaction_removes_it_and_its_tags_and_stops_driving_recs(client, auth_headers):
    alice = auth_headers("user_alice")
    book = await _log(client, alice, "dune", rating=5)
    await client.post(
        f"/interactions/{book['id']}/tags",
        json={"tag_name": "science fiction", "sentiment": "POSITIVE", "category": "GENRE"},
        headers=alice,
    )
    await client.get("/works/search", params={"q": "alien", "medium": "FILM"})
    assert len((await client.get("/recommendations", headers=alice)).json()) > 0

    r = await client.delete(f"/interactions/{book['id']}", headers=alice)
    assert r.status_code == 204 and r.content == b""

    assert (await client.get("/interactions/me", headers=alice)).json() == []
    assert (await client.get(f"/interactions/{book['id']}/tags")).json() == []
    assert (await client.get("/recommendations", headers=alice)).json() == []  # taste signal went with it

    # the work itself stays in the shared catalog and can be logged again
    again = await _log(client, alice, "dune", rating=4)
    assert again["id"] != book["id"]


async def test_delete_interaction_checks_ownership_and_existence(client, auth_headers):
    alice, bob = auth_headers("user_alice"), auth_headers("user_bob")
    book = await _log(client, alice, "dune", rating=5)

    assert (await client.delete(f"/interactions/{book['id']}", headers=bob)).status_code == 403
    assert len((await client.get("/interactions/me", headers=alice)).json()) == 1  # untouched

    assert (await client.delete(f"/interactions/{uuid.uuid4()}", headers=alice)).status_code == 404
    assert (await client.delete(f"/interactions/{book['id']}", headers=alice)).status_code == 204
    assert (await client.delete(f"/interactions/{book['id']}", headers=alice)).status_code == 404  # already gone


async def test_remove_tag_from_interaction(client, auth_headers):
    alice, bob = auth_headers("user_alice"), auth_headers("user_bob")
    book = await _log(client, alice, "dune", rating=5)
    tags = {}
    for name in ("science fiction", "slow burn"):
        r = await client.post(
            f"/interactions/{book['id']}/tags",
            json={"tag_name": name, "sentiment": "POSITIVE", "category": "THEME"},
            headers=alice,
        )
        tags[name] = r.json()["tag_id"]

    assert (await client.delete(f"/interactions/{book['id']}/tags/{tags['slow burn']}", headers=bob)).status_code == 403

    r = await client.delete(f"/interactions/{book['id']}/tags/{tags['slow burn']}", headers=alice)
    assert r.status_code == 204
    remaining = (await client.get(f"/interactions/{book['id']}/tags")).json()
    assert [t["tag_name"].lower() for t in remaining] == ["science fiction"]

    # removing again, or a tag never attached, is a 404; the other tag is unaffected
    assert (await client.delete(f"/interactions/{book['id']}/tags/{tags['slow burn']}", headers=alice)).status_code == 404
    assert (await client.delete(f"/interactions/{book['id']}/tags/{uuid.uuid4()}", headers=alice)).status_code == 404
    assert len((await client.get(f"/interactions/{book['id']}/tags")).json()) == 1


async def test_shelf_pagination_orders_newest_first_and_pages_without_overlap(client, auth_headers):
    alice = auth_headers("user_alice")
    await _log(client, alice, "dune", medium="BOOK", rating=5)
    await _log(client, alice, "dune", medium="FILM", rating=4)
    await _log(client, alice, "alien", medium="FILM", rating=3)

    full = (await client.get("/interactions/me", headers=alice)).json()
    assert [i["work"]["title"] for i in full][0] == "Alien"  # newest first
    assert len(full) == 3

    page1 = (await client.get("/interactions/me", params={"limit": 2}, headers=alice)).json()
    page2 = (await client.get("/interactions/me", params={"limit": 2, "offset": 2}, headers=alice)).json()
    assert [i["id"] for i in page1 + page2] == [i["id"] for i in full]

    assert (await client.get("/interactions/me", params={"offset": 3}, headers=alice)).json() == []
    # the status filter composes with paging
    filtered = (await client.get("/interactions/me", params={"status": "FINISHED", "limit": 1}, headers=alice)).json()
    assert len(filtered) == 1


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "abc"}])
async def test_shelf_rejects_invalid_pagination_params(client, auth_headers, params):
    r = await client.get("/interactions/me", params=params, headers=auth_headers("user_alice"))
    assert r.status_code == 422
