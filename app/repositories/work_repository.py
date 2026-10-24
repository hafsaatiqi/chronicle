import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work import Work
from app.schemas.work import WorkCreate


class WorkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_external_id(self, external_id: str) -> Work | None:
        result = await self.db.execute(select(Work).where(Work.external_id == external_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, work_id: uuid.UUID) -> Work | None:
        result = await self.db.execute(select(Work).where(Work.id == work_id))
        return result.scalar_one_or_none()

    async def create(self, work_data: WorkCreate) -> Work:
        work = Work(**work_data.model_dump())
        self.db.add(work)
        await self.db.flush()
        await self.db.refresh(work)
        return work

    async def search_local(self, query: str, limit: int = 10) -> list[Work]:
        result = await self.db.execute(
            select(Work).where(Work.title.ilike(f"%{query}%")).limit(limit)
        )
        return list(result.scalars().all())
