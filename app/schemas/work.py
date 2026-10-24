import uuid

from pydantic import BaseModel


class WorkCreate(BaseModel):
    medium: str
    title: str
    creator: str
    external_id: str
    synopsis: str | None = None
    cover_url: str | None = None
    subjects: list[str] = []


class WorkResponse(BaseModel):
    id: uuid.UUID
    medium: str
    title: str
    creator: str
    external_id: str
    synopsis: str | None
    cover_url: str | None

    class Config:
        from_attributes = True


class WorkSummary(BaseModel):
    id: uuid.UUID
    medium: str
    title: str
    creator: str
    cover_url: str | None

    class Config:
        from_attributes = True
