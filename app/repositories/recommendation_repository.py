import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tag import Tag
from app.models.user_interaction import UserInteraction
from app.models.user_interaction_tag import UserInteractionTag
from app.models.work import Work
from app.models.work_tag import WorkTag


class RecommendationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_interacted_work_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self.db.execute(
            select(UserInteraction.work_id).where(UserInteraction.user_id == user_id)
        )
        return set(result.scalars().all())

    async def get_user_tag_sentiment_rows(self, user_id: uuid.UUID) -> list[tuple]:
        """(tag_id, tag_name, sentiment, source_work_title) for every tag the user has attached."""
        result = await self.db.execute(
            select(UserInteractionTag.tag_id, Tag.name, UserInteractionTag.sentiment, Work.title)
            .join(Tag, Tag.id == UserInteractionTag.tag_id)
            .join(UserInteraction, UserInteraction.id == UserInteractionTag.interaction_id)
            .join(Work, Work.id == UserInteraction.work_id)
            .where(UserInteraction.user_id == user_id)
        )
        return list(result.all())

    async def get_candidate_works(self, exclude_work_ids: set[uuid.UUID]) -> list[Work]:
        query = select(Work).options(selectinload(Work.work_tags).selectinload(WorkTag.tag))
        if exclude_work_ids:
            query = query.where(Work.id.notin_(exclude_work_ids))
        result = await self.db.execute(query)
        return list(result.scalars().all())
