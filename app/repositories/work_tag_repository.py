import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_tag import WorkTag


class WorkTagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_work_and_tag(self, work_id: uuid.UUID, tag_id: uuid.UUID) -> WorkTag | None:
        result = await self.db.execute(
            select(WorkTag).where(WorkTag.work_id == work_id, WorkTag.tag_id == tag_id)
        )
        return result.scalar_one_or_none()

    async def add_tag_to_work(self, work_id: uuid.UUID, tag_id: uuid.UUID, source: str) -> WorkTag:
        link = WorkTag(work_id=work_id, tag_id=tag_id, source=source)
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link
