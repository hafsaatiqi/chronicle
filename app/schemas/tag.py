import uuid

from pydantic import BaseModel

from app.models.enums import TagCategory


class TagCreate(BaseModel):
    name: str
    category: str = TagCategory.OTHER.value


class TagResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: str

    class Config:
        from_attributes = True


class InteractionTagAttach(BaseModel):
    tag_name: str
    sentiment: str
    category: str = TagCategory.OTHER.value


class InteractionTagResponse(BaseModel):
    tag_id: uuid.UUID
    tag_name: str
    category: str
    sentiment: str
