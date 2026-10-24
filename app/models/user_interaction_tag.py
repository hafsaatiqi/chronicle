import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import Sentiment

if TYPE_CHECKING:
    from app.models.tag import Tag
    from app.models.user_interaction import UserInteraction


class UserInteractionTag(Base):
    __tablename__ = "user_interaction_tags"

    interaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_interactions.id"), primary_key=True, index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True, index=True
    )
    sentiment: Mapped[str] = mapped_column(String, nullable=False, default=Sentiment.POSITIVE.value)

    interaction: Mapped["UserInteraction"] = relationship(back_populates="interaction_tags")
    tag: Mapped["Tag"] = relationship(back_populates="interaction_tags")
