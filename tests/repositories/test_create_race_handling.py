from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.user_repository import UserRepository
from app.repositories.work_repository import WorkRepository
from app.schemas.work import WorkCreate


class FakeSavepoint:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False  # never swallow, like the real thing (it rolls back and re-raises)


def make_db(flush_error: Exception | None) -> MagicMock:
    db = MagicMock()
    db.begin_nested = MagicMock(return_value=FakeSavepoint())
    db.flush = AsyncMock(side_effect=flush_error)
    db.refresh = AsyncMock()
    return db


def integrity_error() -> IntegrityError:
    return IntegrityError("INSERT ...", {}, Exception("duplicate key"))


WORK_DATA = WorkCreate(medium="BOOK", title="Dune", creator="Frank Herbert", external_id="OL1W")


class TestWorkCreate:
    async def test_inserts_normally_without_conflict(self):
        db = make_db(flush_error=None)
        repo = WorkRepository(db)

        work = await repo.create(WORK_DATA)

        assert work.external_id == "OL1W"
        db.add.assert_called_once_with(work)

    async def test_returns_existing_row_on_unique_violation(self):
        db = make_db(flush_error=integrity_error())
        repo = WorkRepository(db)
        winner = MagicMock()
        repo.get_by_external_id = AsyncMock(return_value=winner)

        assert await repo.create(WORK_DATA) is winner
        repo.get_by_external_id.assert_awaited_once_with("OL1W")

    async def test_reraises_when_no_existing_row_explains_the_violation(self):
        db = make_db(flush_error=integrity_error())
        repo = WorkRepository(db)
        repo.get_by_external_id = AsyncMock(return_value=None)

        with pytest.raises(IntegrityError):
            await repo.create(WORK_DATA)


class TestUserCreate:
    async def test_inserts_normally_without_conflict(self):
        db = make_db(flush_error=None)
        repo = UserRepository(db)

        user = await repo.create("clerk_1", "a@b.com", "A B")

        assert user.clerk_id == "clerk_1"

    async def test_returns_existing_row_on_clerk_id_race(self):
        db = make_db(flush_error=integrity_error())
        repo = UserRepository(db)
        winner = MagicMock()
        repo.get_by_clerk_id = AsyncMock(return_value=winner)

        assert await repo.create("clerk_1", "a@b.com", "A B") is winner

    async def test_reraises_when_violation_is_not_a_clerk_id_race(self):
        # e.g. the email already belongs to a different Clerk account
        db = make_db(flush_error=integrity_error())
        repo = UserRepository(db)
        repo.get_by_clerk_id = AsyncMock(return_value=None)

        with pytest.raises(IntegrityError):
            await repo.create("clerk_1", "taken@b.com", "A B")
