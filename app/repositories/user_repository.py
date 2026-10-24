from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_clerk_id(self, clerk_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.clerk_id == clerk_id))
        return result.scalar_one_or_none()

    async def create(self, clerk_id: str, email: str, display_name: str) -> User:
        user = User(clerk_id=clerk_id, email=email, display_name=display_name)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
