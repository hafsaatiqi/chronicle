import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.tag_service import TagService


def make_service() -> TagService:
    service = TagService(db=MagicMock())
    service.db.commit = AsyncMock()
    service.tag_repository = AsyncMock()
    service.interaction_tag_repository = AsyncMock()
    service.interaction_repository = AsyncMock()
    return service


def make_interaction(user_id):
    return SimpleNamespace(id=uuid.uuid4(), user_id=user_id)


OWNER_ID = uuid.uuid4()
OWNER = SimpleNamespace(id=OWNER_ID)


async def test_tagging_own_interaction_creates_new_tag_link():
    service = make_service()
    interaction = make_interaction(OWNER_ID)
    service.interaction_repository.get_by_id.return_value = interaction
    tag = SimpleNamespace(id=uuid.uuid4(), name="Slow Burn", category="PACING")
    service.tag_repository.get_or_create.return_value = tag
    service.interaction_tag_repository.get_by_interaction_and_tag.return_value = None

    response = await service.tag_interaction(OWNER, interaction.id, "Slow Burn", "PACING", "POSITIVE")

    service.interaction_tag_repository.add_tag_to_interaction.assert_awaited_once_with(
        interaction.id, tag.id, "POSITIVE"
    )
    service.interaction_tag_repository.update_sentiment.assert_not_called()
    assert response.tag_name == "Slow Burn"
    assert response.sentiment == "POSITIVE"


async def test_retagging_existing_link_updates_sentiment_instead_of_duplicating():
    service = make_service()
    interaction = make_interaction(OWNER_ID)
    service.interaction_repository.get_by_id.return_value = interaction
    tag = SimpleNamespace(id=uuid.uuid4(), name="Slow Burn", category="PACING")
    service.tag_repository.get_or_create.return_value = tag
    existing_link = SimpleNamespace(tag_id=tag.id)
    service.interaction_tag_repository.get_by_interaction_and_tag.return_value = existing_link

    await service.tag_interaction(OWNER, interaction.id, "Slow Burn", "PACING", "NEGATIVE")

    service.interaction_tag_repository.update_sentiment.assert_awaited_once_with(existing_link, "NEGATIVE")
    service.interaction_tag_repository.add_tag_to_interaction.assert_not_called()


async def test_tagging_another_users_interaction_is_forbidden():
    service = make_service()
    other_users_interaction = make_interaction(uuid.uuid4())
    service.interaction_repository.get_by_id.return_value = other_users_interaction

    with pytest.raises(HTTPException) as exc_info:
        await service.tag_interaction(OWNER, other_users_interaction.id, "Slow Burn", "PACING", "POSITIVE")

    assert exc_info.value.status_code == 403
    service.tag_repository.get_or_create.assert_not_called()


async def test_tagging_nonexistent_interaction_is_not_found():
    service = make_service()
    service.interaction_repository.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await service.tag_interaction(OWNER, uuid.uuid4(), "Slow Burn", "PACING", "POSITIVE")

    assert exc_info.value.status_code == 404


async def test_invalid_sentiment_is_rejected():
    service = make_service()
    interaction = make_interaction(OWNER_ID)
    service.interaction_repository.get_by_id.return_value = interaction

    with pytest.raises(HTTPException) as exc_info:
        await service.tag_interaction(OWNER, interaction.id, "Slow Burn", "PACING", "MEH")

    assert exc_info.value.status_code == 422
    service.tag_repository.get_or_create.assert_not_called()


async def test_list_tags_has_no_ownership_check():
    service = make_service()
    tag = SimpleNamespace(name="Slow Burn", category="PACING")
    link = SimpleNamespace(tag_id=uuid.uuid4(), tag=tag, sentiment="POSITIVE")
    service.interaction_tag_repository.list_tags_for_interaction.return_value = [link]

    result = await service.list_tags(uuid.uuid4())

    assert len(result) == 1
    assert result[0].tag_name == "Slow Burn"


async def test_removing_own_tag_deletes_link_and_commits():
    service = make_service()
    interaction = make_interaction(OWNER_ID)
    service.interaction_repository.get_by_id.return_value = interaction
    tag_id = uuid.uuid4()
    service.interaction_tag_repository.get_by_interaction_and_tag.return_value = SimpleNamespace(tag_id=tag_id)

    await service.remove_tag(OWNER, interaction.id, tag_id)

    service.interaction_tag_repository.remove_tag_from_interaction.assert_awaited_once_with(interaction.id, tag_id)
    service.db.commit.assert_awaited_once()


async def test_removing_tag_not_on_interaction_raises_404():
    service = make_service()
    interaction = make_interaction(OWNER_ID)
    service.interaction_repository.get_by_id.return_value = interaction
    service.interaction_tag_repository.get_by_interaction_and_tag.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await service.remove_tag(OWNER, interaction.id, uuid.uuid4())

    assert exc_info.value.status_code == 404
    service.interaction_tag_repository.remove_tag_from_interaction.assert_not_called()


async def test_removing_tag_on_someone_elses_interaction_raises_403():
    service = make_service()
    interaction = make_interaction(uuid.uuid4())
    service.interaction_repository.get_by_id.return_value = interaction

    with pytest.raises(HTTPException) as exc_info:
        await service.remove_tag(OWNER, interaction.id, uuid.uuid4())

    assert exc_info.value.status_code == 403
    service.interaction_tag_repository.remove_tag_from_interaction.assert_not_called()
