from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag


class TagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_name(self, name: str) -> Tag | None:
        normalized = name.strip().lower()
        result = await self.db.execute(select(Tag).where(func.lower(Tag.name) == normalized))
        return result.scalar_one_or_none()

    async def create(self, name: str, category: str) -> Tag:
        tag = Tag(name=name.strip(), category=category)
        self.db.add(tag)
        await self.db.flush()
        await self.db.refresh(tag)
        return tag

    async def get_or_create(self, name: str, category: str) -> Tag:
        existing = await self.get_by_name(name)
        if existing is not None:
            return existing
        return await self.create(name, category)
