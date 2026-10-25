import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
        """Insert a work; if a concurrent request already created this external_id, return that row instead."""
        work = Work(**work_data.model_dump(exclude={"subjects"}))
        try:
            # Savepoint, so a unique violation doesn't poison the caller's whole transaction.
            async with self.db.begin_nested():
                self.db.add(work)
                await self.db.flush()
        except IntegrityError:
            existing = await self.get_by_external_id(work_data.external_id)
            if existing is None:
                raise
            return existing
        await self.db.refresh(work)
        return work

    async def search_local(self, query: str, medium: str, limit: int = 10) -> list[Work]:
        result = await self.db.execute(
            select(Work)
            .where(Work.title.ilike(f"%{query}%"), Work.medium == medium)
            .limit(limit)
        )
        return list(result.scalars().all())
