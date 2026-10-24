import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import TagSource

if TYPE_CHECKING:
    from app.models.tag import Tag
    from app.models.work import Work


class WorkTag(Base):
    __tablename__ = "work_tags"

    work_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("works.id"), primary_key=True, index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True, index=True
    )
    source: Mapped[str] = mapped_column(String, nullable=False, default=TagSource.CATALOG.value)

    work: Mapped["Work"] = relationship(back_populates="work_tags")
    tag: Mapped["Tag"] = relationship(back_populates="work_tags")
