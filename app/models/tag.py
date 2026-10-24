import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import TagCategory

if TYPE_CHECKING:
    from app.models.user_interaction_tag import UserInteractionTag
    from app.models.work_tag import WorkTag


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, default=TagCategory.OTHER.value)

    work_tags: Mapped[list["WorkTag"]] = relationship(back_populates="tag")
    interaction_tags: Mapped[list["UserInteractionTag"]] = relationship(back_populates="tag")
