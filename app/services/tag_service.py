import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Sentiment
from app.models.user import User
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.interaction_tag_repository import InteractionTagRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.tag import InteractionTagResponse

_VALID_SENTIMENTS = {s.value for s in Sentiment}


class TagService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tag_repository = TagRepository(db)
        self.interaction_tag_repository = InteractionTagRepository(db)
        self.interaction_repository = InteractionRepository(db)

    async def tag_interaction(
        self,
        user: User,
        interaction_id: uuid.UUID,
        tag_name: str,
        category: str,
        sentiment: str,
    ) -> InteractionTagResponse:
        interaction = await self._get_owned_interaction(user, interaction_id)

        if sentiment not in _VALID_SENTIMENTS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid sentiment '{sentiment}'",
            )

        tag = await self.tag_repository.get_or_create(tag_name, category)

        existing_link = await self.interaction_tag_repository.get_by_interaction_and_tag(
            interaction.id, tag.id
        )
        if existing_link is not None:
            await self.interaction_tag_repository.update_sentiment(existing_link, sentiment)
        else:
            await self.interaction_tag_repository.add_tag_to_interaction(interaction.id, tag.id, sentiment)

        await self.db.commit()

        return InteractionTagResponse(tag_id=tag.id, tag_name=tag.name, category=tag.category, sentiment=sentiment)

    async def list_tags(self, interaction_id: uuid.UUID) -> list[InteractionTagResponse]:
        links = await self.interaction_tag_repository.list_tags_for_interaction(interaction_id)
        return [
            InteractionTagResponse(
                tag_id=link.tag_id,
                tag_name=link.tag.name,
                category=link.tag.category,
                sentiment=link.sentiment,
            )
            for link in links
        ]

    async def _get_owned_interaction(self, user: User, interaction_id: uuid.UUID):
        interaction = await self.interaction_repository.get_by_id(interaction_id)
        if interaction is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
        if interaction.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this interaction",
            )
        return interaction
