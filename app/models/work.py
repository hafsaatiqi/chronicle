import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import Medium

if TYPE_CHECKING:
    from app.models.user_interaction import UserInteraction
    from app.models.work_tag import WorkTag


class Work(Base):
    __tablename__ = "works"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medium: Mapped[str] = mapped_column(String, nullable=False, default=Medium.BOOK.value)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    creator: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    synopsis: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    interactions: Mapped[list["UserInteraction"]] = relationship(back_populates="work")
    work_tags: Mapped[list["WorkTag"]] = relationship(back_populates="work")
