"""The check-then-insert race fixes, proven with truly concurrent sessions against real Postgres."""
import asyncio

import pytest
from sqlalchemy import text

from app.repositories.tag_repository import TagRepository
from app.repositories.user_repository import UserRepository
from app.repositories.work_repository import WorkRepository
from app.schemas.work import WorkCreate

pytestmark = pytest.mark.integration

CONCURRENCY = 8


async def _run_concurrently(session_maker, create):
    async def attempt():
        async with session_maker() as db:
            row = await create(db)
            await asyncio.sleep(0.05)  # hold the transaction open so the others genuinely collide
            await db.commit()
            return row.id

    return await asyncio.gather(*[attempt() for _ in range(CONCURRENCY)])


async def _count(session_maker, sql: str) -> int:
    async with session_maker() as db:
        return (await db.execute(text(sql))).scalar()


async def test_concurrent_work_creates_yield_one_row(session_maker):
    data = WorkCreate(medium="BOOK", title="Race", creator="x", external_id="OL-RACE")

    ids = await _run_concurrently(session_maker, lambda db: WorkRepository(db).create(data))

    assert len(set(ids)) == 1
    assert await _count(session_maker, "SELECT count(*) FROM works") == 1


async def test_concurrent_user_creates_yield_one_row(session_maker):
    ids = await _run_concurrently(
        session_maker, lambda db: UserRepository(db).create("user_race", "race@test.dev", "Race")
    )

    assert len(set(ids)) == 1
    assert await _count(session_maker, "SELECT count(*) FROM users") == 1


async def test_concurrent_tag_creates_yield_one_row(session_maker):
    ids = await _run_concurrently(session_maker, lambda db: TagRepository(db).get_or_create("Slow Burn", "PACING"))

    assert len(set(ids)) == 1
    assert await _count(session_maker, "SELECT count(*) FROM tags") == 1


async def test_email_collision_with_a_different_clerk_id_is_not_masked(session_maker):
    from sqlalchemy.exc import IntegrityError

    async with session_maker() as db:
        await UserRepository(db).create("user_a", "same@test.dev", "A")
        await db.commit()

    async with session_maker() as db:
        with pytest.raises(IntegrityError):
            await UserRepository(db).create("user_b", "same@test.dev", "B")
