from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import Work
from app.repositories.work_repository import WorkRepository
from app.services.open_library_service import OpenLibraryService


RESULT_LIMIT = 10


class WorkService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.work_repository = WorkRepository(db)
        self.open_library_service = OpenLibraryService()

    async def search_or_create(self, query: str) -> list[Work]:
        local_results = await self.work_repository.search_local(query, limit=RESULT_LIMIT)
        known_external_ids = {work.external_id for work in local_results}

        external_results = await self.open_library_service.search(query)

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
            newly_created.append(created)
            known_external_ids.add(created.external_id)

        if newly_created:
            await self.db.commit()

        return local_results + newly_created
