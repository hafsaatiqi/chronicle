"""The product's core loop through the real HTTP + dependency-injection stack:
search -> log -> tag -> recommend, including the cross-medium (book -> film) path."""
import uuid

import pytest

pytestmark = pytest.mark.integration


async def test_search_log_tag_recommend_across_mediums(client, auth_headers):
    alice = auth_headers("user_alice")

    # --- search (lazy ingestion): book is created from the mocked Open Library response
    r = await client.get("/works/search", params={"q": "dune"})
    assert r.status_code == 200
    books = r.json()
    assert [b["title"] for b in books] == ["Dune"] and books[0]["medium"] == "BOOK"
    book_id = books[0]["id"]

    # searching again must not duplicate the work
    again = (await client.get("/works/search", params={"q": "dune"})).json()
    assert [b["id"] for b in again] == [book_id]

    # public single-work lookup
    r = await client.get(f"/works/{book_id}")
    assert r.status_code == 200 and r.json()["creator"] == "Frank Herbert"

    # --- log: rating alone defaults to FINISHED; logging again upserts rather than duplicating
    r = await client.post("/interactions", json={"work_id": book_id, "rating": 5}, headers=alice)
    assert r.status_code == 200
    interaction = r.json()
    assert interaction["status"] == "FINISHED" and interaction["rating"] == 5
    assert interaction["work"]["title"] == "Dune"  # nested WorkSummary for the shelf

    r = await client.post("/interactions", json={"work_id": book_id, "rating": 4}, headers=alice)
    assert r.json()["id"] == interaction["id"] and r.json()["rating"] == 4

    shelf = (await client.get("/interactions/me", headers=alice)).json()
    assert len(shelf) == 1 and shelf[0]["rating"] == 4
    assert len((await client.get("/interactions/me", params={"status": "FINISHED"}, headers=alice)).json()) == 1
    assert (await client.get("/interactions/me", params={"status": "WANT_TO"}, headers=alice)).json() == []

    # --- tag with sentiment (auth required); reading tags is public
    r = await client.post(
        f"/interactions/{interaction['id']}/tags",
        json={"tag_name": "science fiction", "sentiment": "POSITIVE", "category": "GENRE"},
        headers=alice,
    )
    assert r.status_code == 200 and r.json()["sentiment"] == "POSITIVE"
    public_tags = (await client.get(f"/interactions/{interaction['id']}/tags")).json()
    assert [t["tag_name"].lower() for t in public_tags] == ["science fiction"]

    # --- ingest films (mocked TMDB), then recommend
    for query in ("dune", "alien", "pride"):
        r = await client.get("/works/search", params={"q": query, "medium": "FILM"})
        assert r.status_code == 200 and r.json()[0]["medium"] == "FILM"

    recs = (await client.get("/recommendations", headers=alice)).json()
    by_title = {rec["work"]["title"]: rec for rec in recs}

    # the book drove FILM recommendations through a shared tag (cross-media thesis)
    assert {"Dune", "Alien"} <= set(by_title)
    dune_film = by_title["Dune"]
    assert dune_film["work"]["medium"] == "FILM" and dune_film["work"]["id"] != book_id
    assert dune_film["score"] == 1
    match = dune_film["matched_tags"][0]
    assert match["tag_name"].lower() == "science fiction"
    assert match["sentiment"] == "POSITIVE" and match["source_works"] == ["Dune"]
    assert "Pride and Prejudice" not in by_title  # no overlapping tags

    # --- negative signal: disliking "horror" cancels Alien's sci-fi match (net 0 -> excluded)
    r = await client.post(
        f"/interactions/{interaction['id']}/tags",
        json={"tag_name": "Horror", "sentiment": "NEGATIVE", "category": "GENRE"},
        headers=alice,
    )
    assert r.status_code == 200
    titles = {rec["work"]["title"] for rec in (await client.get("/recommendations", headers=alice)).json()}
    assert titles == {"Dune"}


async def test_auth_me_provisions_and_reuses_local_user(client, auth_headers):
    first = await client.get("/auth/me", headers=auth_headers("user_alice"))
    assert first.status_code == 200
    body = first.json()
    assert body["email"] == "user_alice@test.dev" and body["display_name"] == "Test user_alice"

    second = await client.get("/auth/me", headers=auth_headers("user_alice"))
    assert second.json()["id"] == body["id"]  # same local row, not re-provisioned

    other = await client.get("/auth/me", headers=auth_headers("user_bob"))
    assert other.json()["id"] != body["id"]


async def test_users_cannot_tag_each_others_interactions_and_start_cold(client, auth_headers):
    alice, bob = auth_headers("user_alice"), auth_headers("user_bob")
    book_id = (await client.get("/works/search", params={"q": "dune"})).json()[0]["id"]
    interaction_id = (await client.post("/interactions", json={"work_id": book_id, "rating": 5}, headers=alice)).json()["id"]

    r = await client.post(
        f"/interactions/{interaction_id}/tags",
        json={"tag_name": "mine", "sentiment": "POSITIVE"},
        headers=bob,
    )
    assert r.status_code == 403
    assert (await client.get("/interactions/me", headers=bob)).json() == []
    assert (await client.get("/recommendations", headers=bob)).json() == []  # cold start, no 500

    r = await client.post(
        f"/interactions/{uuid.uuid4()}/tags", json={"tag_name": "x", "sentiment": "POSITIVE"}, headers=alice
    )
    assert r.status_code == 404
