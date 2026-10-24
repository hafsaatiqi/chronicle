import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_interaction import UserInteraction


class InteractionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_and_work(self, user_id: uuid.UUID, work_id: uuid.UUID) -> UserInteraction | None:
        result = await self.db.execute(
            select(UserInteraction).where(
                UserInteraction.user_id == user_id, UserInteraction.work_id == work_id
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        work_id: uuid.UUID,
        status: str,
        rating: int | None,
        review_text: str | None,
    ) -> UserInteraction:
        interaction = UserInteraction(
            user_id=user_id,
            work_id=work_id,
            status=status,
            rating=rating,
            review_text=review_text,
        )
        self.db.add(interaction)
        await self.db.flush()
        await self.db.refresh(interaction)
        return interaction

    async def update(
        self,
        interaction: UserInteraction,
        status: str,
        rating: int | None,
        review_text: str | None,
    ) -> UserInteraction:
        interaction.status = status
        interaction.rating = rating
        interaction.review_text = review_text
        await self.db.flush()
        await self.db.refresh(interaction)
        return interaction

    async def list_by_user(self, user_id: uuid.UUID, status: str | None = None) -> list[UserInteraction]:
        query = select(UserInteraction).where(UserInteraction.user_id == user_id)
        if status is not None:
            query = query.where(UserInteraction.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())
