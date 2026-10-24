import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.interaction import InteractionCreate
from app.services.interaction_service import InteractionService


def make_service() -> InteractionService:
    service = InteractionService(db=MagicMock())
    service.db.commit = AsyncMock()
    service.interaction_repository = AsyncMock()
    service.work_repository = AsyncMock()
    return service


OWNER = SimpleNamespace(id=uuid.uuid4())


class TestResolveStatus:
    def test_rating_with_no_status_defaults_to_finished(self):
        service = make_service()

        assert service._resolve_status(None, rating=5) == "FINISHED"

    def test_no_status_and_no_rating_is_rejected(self):
        service = make_service()

        with pytest.raises(HTTPException) as exc_info:
            service._resolve_status(None, rating=None)

        assert exc_info.value.status_code == 422

    def test_status_with_no_rating_is_allowed_for_any_valid_status(self):
        service = make_service()

        assert service._resolve_status("IN_PROGRESS", rating=None) == "IN_PROGRESS"

    def test_invalid_status_is_rejected(self):
        service = make_service()

        with pytest.raises(HTTPException) as exc_info:
            service._resolve_status("NOT_A_REAL_STATUS", rating=None)

        assert exc_info.value.status_code == 422

    def test_rating_on_in_progress_status_is_rejected(self):
        service = make_service()

        with pytest.raises(HTTPException) as exc_info:
            service._resolve_status("IN_PROGRESS", rating=4)

        assert exc_info.value.status_code == 422

    @pytest.mark.parametrize("allowed_status", ["FINISHED", "DROPPED"])
    def test_rating_is_allowed_with_finished_or_dropped(self, allowed_status):
        service = make_service()

        assert service._resolve_status(allowed_status, rating=5) == allowed_status


class TestLogInteraction:
    async def test_work_not_found_raises_404(self):
        service = make_service()
        service.work_repository.get_by_id.return_value = None
        data = InteractionCreate(work_id=uuid.uuid4(), rating=5)

        with pytest.raises(HTTPException) as exc_info:
            await service.log_interaction(OWNER, data)

        assert exc_info.value.status_code == 404
        service.interaction_repository.create.assert_not_called()

    async def test_new_interaction_is_created_with_resolved_status(self):
        service = make_service()
        service.work_repository.get_by_id.return_value = SimpleNamespace(id=uuid.uuid4())
        service.interaction_repository.get_by_user_and_work.return_value = None
        work_id = uuid.uuid4()
        data = InteractionCreate(work_id=work_id, rating=5)

        await service.log_interaction(OWNER, data)

        service.interaction_repository.create.assert_awaited_once_with(OWNER.id, work_id, "FINISHED", 5, None)
        service.interaction_repository.update.assert_not_called()
        service.db.commit.assert_awaited_once()

    async def test_existing_interaction_is_updated_not_duplicated(self):
        service = make_service()
        service.work_repository.get_by_id.return_value = SimpleNamespace(id=uuid.uuid4())
        existing = SimpleNamespace(id=uuid.uuid4())
        service.interaction_repository.get_by_user_and_work.return_value = existing
        data = InteractionCreate(work_id=uuid.uuid4(), status="IN_PROGRESS")

        await service.log_interaction(OWNER, data)

        service.interaction_repository.update.assert_awaited_once_with(
            existing, status="IN_PROGRESS", rating=None, review_text=None
        )
        service.interaction_repository.create.assert_not_called()


class TestListMyShelf:
    async def test_invalid_status_filter_is_rejected(self):
        service = make_service()

        with pytest.raises(HTTPException) as exc_info:
            await service.list_my_shelf(OWNER, "NOT_A_REAL_STATUS")

        assert exc_info.value.status_code == 422

    async def test_valid_status_filter_passes_through(self):
        service = make_service()
        service.interaction_repository.list_by_user.return_value = []

        await service.list_my_shelf(OWNER, "FINISHED")

        service.interaction_repository.list_by_user.assert_awaited_once_with(OWNER.id, "FINISHED")
