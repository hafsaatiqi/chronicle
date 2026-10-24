from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Medium, TagCategory, TagSource
from app.models.work import Work
from app.repositories.tag_repository import TagRepository
from app.repositories.work_repository import WorkRepository
from app.repositories.work_tag_repository import WorkTagRepository
from app.services.open_library_service import OpenLibraryService
from app.services.tmdb_service import TMDBService

RESULT_LIMIT = 10
MAX_CATALOG_TAGS_PER_WORK = 5
_MAX_SUBJECT_LENGTH = 40

_JUNK_SUBJECT_SUBSTRINGS = {
    "accessible book",
    "protected daisy",
    "in library",
    "overdrive",
    "lending library",
    "internet archive",
    "large type books",
    "open library staff pick",
    "popular print disabled books",
    "new york times",
    "bestseller",
    "reviewed",
    "nyt:",
}

_GENRE_KEYWORDS = {
    "fiction",
    "fantasy",
    "mystery",
    "romance",
    "horror",
    "thriller",
    "biography",
    "poetry",
    "drama",
    "adventure",
    "sci-fi",
    "comics",
    "graphic novels",
}


class WorkService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.work_repository = WorkRepository(db)
        self.tag_repository = TagRepository(db)
        self.work_tag_repository = WorkTagRepository(db)
        self._external_services = {
            Medium.BOOK.value: OpenLibraryService(),
            Medium.FILM.value: TMDBService(),
        }

    async def search_or_create(self, query: str, medium: str = Medium.BOOK.value) -> list[Work]:
        local_results = await self.work_repository.search_local(query, medium, limit=RESULT_LIMIT)
        known_external_ids = {work.external_id for work in local_results}

        external_results = await self._external_services[medium].search(query)

        newly_created: list[Work] = []
        for work_data in external_results:
            if len(local_results) + len(newly_created) >= RESULT_LIMIT:
                break
            if work_data.external_id in known_external_ids:
                continue
            existing = await self.work_repository.get_by_external_id(work_data.external_id)
            if existing is not None:
                newly_created.append(existing)
                known_external_ids.add(existing.external_id)
                continue
            created = await self.work_repository.create(work_data)
            await self._attach_catalog_tags(created, work_data.subjects)
            newly_created.append(created)
            known_external_ids.add(created.external_id)

        if newly_created:
            await self.db.commit()

        return local_results + newly_created

    async def _attach_catalog_tags(self, work: Work, subjects: list[str]) -> None:
        for name, category in self._select_tag_candidates(subjects):
            tag = await self.tag_repository.get_or_create(name, category)
            existing_link = await self.work_tag_repository.get_by_work_and_tag(work.id, tag.id)
            if existing_link is None:
                await self.work_tag_repository.add_tag_to_work(work.id, tag.id, TagSource.CATALOG.value)

    def _select_tag_candidates(self, subjects: list[str]) -> list[tuple[str, str]]:
        seen: set[str] = set()
        candidates: list[tuple[str, str]] = []
        for subject in subjects:
            cleaned = subject.strip()
            key = cleaned.lower()
            if not cleaned or key in seen:
                continue
            if (
                len(cleaned) > _MAX_SUBJECT_LENGTH
                or "--" in cleaned
                or "/" in cleaned
                or ":" in cleaned
                or "�" in cleaned
                or any(junk in key for junk in _JUNK_SUBJECT_SUBSTRINGS)
            ):
                continue
            seen.add(key)
            category = TagCategory.GENRE.value if any(g in key for g in _GENRE_KEYWORDS) else TagCategory.THEME.value
            candidates.append((cleaned, category))
            if len(candidates) >= MAX_CATALOG_TAGS_PER_WORK:
                break
        return candidates
