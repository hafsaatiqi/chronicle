from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_clerk_id(self, clerk_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.clerk_id == clerk_id))
        return result.scalar_one_or_none()

    async def create(self, clerk_id: str, email: str, display_name: str) -> User:
        """Insert a user; if a concurrent request already created this clerk_id, return that row instead."""
        user = User(clerk_id=clerk_id, email=email, display_name=display_name)
        try:
            # Savepoint, so a unique violation doesn't poison the caller's whole transaction.
            async with self.db.begin_nested():
                self.db.add(user)
                await self.db.flush()
        except IntegrityError:
            existing = await self.get_by_clerk_id(clerk_id)
            if existing is None:
                # Not a clerk_id race (e.g. the email belongs to a different account) -- don't mask it.
                raise
            return existing
        await self.db.refresh(user)
        return user
