import uuid

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

from app.models.enums import Medium
from app.schemas.work import WorkCreate
from app.services.work_service import MAX_CATALOG_TAGS_PER_WORK, WorkService


def make_service() -> WorkService:
    return WorkService(db=MagicMock())


class TestSelectTagCandidates:
    def test_filters_known_junk_subjects(self):
        service = make_service()
        subjects = [
            "Protected DAISY",
            "Accessible book",
            "New York Times bestseller",
            "nyt:hardcover-fiction=2021-05-23",
            "In library",
        ]

        assert service._select_tag_candidates(subjects) == []

    def test_filters_overly_long_subjects(self):
        service = make_service()
        long_subject = "A" * 41

        assert service._select_tag_candidates([long_subject]) == []

    def test_filters_lcsh_subdivisions(self):
        service = make_service()
        subjects = ["Science fiction, American -- History and criticism"]

        assert service._select_tag_candidates(subjects) == []

    def test_filters_slash_and_colon_formatted_entries(self):
        service = make_service()
        subjects = [
            "FICTION / Science Fiction / Action & Adventure",
            "nyt:trade-fiction-paperback=2022-11-13",
        ]

        assert service._select_tag_candidates(subjects) == []

    def test_filters_encoding_mangled_entries(self):
        service = make_service()
        subjects = ["Habilet�s de survie"]

        assert service._select_tag_candidates(subjects) == []

    def test_dedupes_case_insensitively(self):
        service = make_service()
        subjects = ["Science Fiction", "science fiction", "SCIENCE FICTION"]

        candidates = service._select_tag_candidates(subjects)

        assert len(candidates) == 1
        assert candidates[0][0] == "Science Fiction"

    def test_caps_results_at_max_per_work(self):
        service = make_service()
        subjects = [f"Theme {i}" for i in range(MAX_CATALOG_TAGS_PER_WORK + 10)]

        candidates = service._select_tag_candidates(subjects)

        assert len(candidates) == MAX_CATALOG_TAGS_PER_WORK

    def test_categorizes_genre_keywords_as_genre(self):
        service = make_service()

        candidates = service._select_tag_candidates(["Science fiction", "hard sci-fi"])

        assert all(category == "GENRE" for _, category in candidates)

    def test_categorizes_non_genre_subjects_as_theme(self):
        service = make_service()

        candidates = service._select_tag_candidates(["End of the world"])

        assert candidates == [("End of the world", "THEME")]


class TestSearchOrCreateMediumDispatch:
    def _make_service_with_fakes(self):
        service = make_service()
        service.work_repository = AsyncMock()
        service.work_repository.search_local.return_value = []
        service.work_repository.get_by_external_id.return_value = None
        service._attach_catalog_tags = AsyncMock()
        service.db.commit = AsyncMock()

        book_service = AsyncMock()
        film_service = AsyncMock()
        service._external_services = {
            Medium.BOOK.value: book_service,
            Medium.FILM.value: film_service,
        }
        return service, book_service, film_service

    async def test_default_medium_dispatches_to_book_service(self):
        service, book_service, film_service = self._make_service_with_fakes()
        book_service.search.return_value = []

        await service.search_or_create("Dune")

        book_service.search.assert_awaited_once_with("Dune")
        film_service.search.assert_not_called()

    async def test_film_medium_dispatches_to_tmdb_service(self):
        service, book_service, film_service = self._make_service_with_fakes()
        film_service.search.return_value = []

        await service.search_or_create("Dune", Medium.FILM.value)

        film_service.search.assert_awaited_once_with("Dune")
        book_service.search.assert_not_called()

    async def test_new_external_result_is_created_and_tagged(self):
        service, book_service, _ = self._make_service_with_fakes()
        work_data = WorkCreate(
            medium=Medium.BOOK.value,
            title="Dune",
            creator="Frank Herbert",
            external_id="OL1W",
            subjects=["Science fiction"],
        )
        book_service.search.return_value = [work_data]
        created_work = MagicMock()
        service.work_repository.create.return_value = created_work

        results = await service.search_or_create("Dune")

        service.work_repository.create.assert_awaited_once_with(work_data)
        service._attach_catalog_tags.assert_awaited_once_with(created_work, ["Science fiction"])
        assert results == [created_work]
        service.db.commit.assert_awaited_once()

    async def test_result_already_known_locally_is_not_recreated(self):
        service, book_service, _ = self._make_service_with_fakes()
        local_work = MagicMock(external_id="OL1W")
        service.work_repository.search_local.return_value = [local_work]
        work_data = WorkCreate(medium=Medium.BOOK.value, title="Dune", creator="x", external_id="OL1W")
        book_service.search.return_value = [work_data]

        results = await service.search_or_create("Dune")

        service.work_repository.create.assert_not_called()
        assert results == [local_work]

    async def test_result_existing_by_external_id_is_reused_not_recreated(self):
        service, book_service, _ = self._make_service_with_fakes()
        existing_work = MagicMock(external_id="OL2W")
        service.work_repository.get_by_external_id.return_value = existing_work
        work_data = WorkCreate(medium=Medium.BOOK.value, title="Dune Messiah", creator="x", external_id="OL2W")
        book_service.search.return_value = [work_data]

        results = await service.search_or_create("Dune")

        service.work_repository.create.assert_not_called()
        assert results == [existing_work]
        service.db.commit.assert_awaited_once()

    async def test_no_new_works_skips_commit(self):
        service, book_service, _ = self._make_service_with_fakes()
        book_service.search.return_value = []

        await service.search_or_create("Dune")

        service.db.commit.assert_not_called()


class TestGetWork:
    async def test_returns_work_when_found(self):
        service = make_service()
        work = MagicMock()
        service.work_repository.get_by_id = AsyncMock(return_value=work)
        work_id = uuid.uuid4()

        result = await service.get_work(work_id)

        assert result is work
        service.work_repository.get_by_id.assert_awaited_once_with(work_id)

    async def test_raises_404_when_missing(self):
        service = make_service()
        service.work_repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await service.get_work(uuid.uuid4())

        assert exc.value.status_code == 404
