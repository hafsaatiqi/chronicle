import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InteractionCreate(BaseModel):
    work_id: uuid.UUID
    status: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    review_text: str | None = None


class InteractionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    work_id: uuid.UUID
    status: str
    rating: int | None
    review_text: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
