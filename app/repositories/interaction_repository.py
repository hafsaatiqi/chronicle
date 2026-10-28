import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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

    async def get_by_id(self, interaction_id: uuid.UUID) -> UserInteraction | None:
        result = await self.db.execute(select(UserInteraction).where(UserInteraction.id == interaction_id))
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
        await self.db.refresh(interaction, attribute_names=["work"])
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
        # updated_at is regenerated server-side (onupdate=func.now()), which expires it on the instance;
        # reload it here, since async SQLAlchemy can't lazy-load it later during response serialization.
        await self.db.refresh(interaction, attribute_names=["work", "updated_at"])
        return interaction

    async def list_by_user(
        self, user_id: uuid.UUID, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[UserInteraction]:
        query = select(UserInteraction).options(selectinload(UserInteraction.work)).where(
            UserInteraction.user_id == user_id
        )
        if status is not None:
            query = query.where(UserInteraction.status == status)
        # id is a tiebreaker so pages stay stable when created_at collides
        query = query.order_by(UserInteraction.created_at.desc(), UserInteraction.id).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete(self, interaction: UserInteraction) -> None:
        await self.db.delete(interaction)
        await self.db.flush()
