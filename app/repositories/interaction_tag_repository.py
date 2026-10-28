import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user_interaction_tag import UserInteractionTag


class InteractionTagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_interaction_and_tag(
        self, interaction_id: uuid.UUID, tag_id: uuid.UUID
    ) -> UserInteractionTag | None:
        result = await self.db.execute(
            select(UserInteractionTag).where(
                UserInteractionTag.interaction_id == interaction_id,
                UserInteractionTag.tag_id == tag_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_tag_to_interaction(
        self, interaction_id: uuid.UUID, tag_id: uuid.UUID, sentiment: str
    ) -> UserInteractionTag:
        link = UserInteractionTag(interaction_id=interaction_id, tag_id=tag_id, sentiment=sentiment)
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def update_sentiment(self, link: UserInteractionTag, sentiment: str) -> UserInteractionTag:
        link.sentiment = sentiment
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def list_tags_for_interaction(self, interaction_id: uuid.UUID) -> list[UserInteractionTag]:
        result = await self.db.execute(
            select(UserInteractionTag)
            .options(selectinload(UserInteractionTag.tag))
            .where(UserInteractionTag.interaction_id == interaction_id)
        )
        return list(result.scalars().all())

    async def remove_tag_from_interaction(self, interaction_id: uuid.UUID, tag_id: uuid.UUID) -> None:
        link = await self.get_by_interaction_and_tag(interaction_id, tag_id)
        if link is not None:
            await self.db.delete(link)
            await self.db.flush()

    async def remove_all_for_interaction(self, interaction_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(UserInteractionTag).where(UserInteractionTag.interaction_id == interaction_id)
        )
        await self.db.flush()
