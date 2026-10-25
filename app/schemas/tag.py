import uuid

from pydantic import BaseModel, field_validator

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

    @field_validator("category")
    @classmethod
    def _category_must_be_known(cls, value: str) -> str:
        if value not in {c.value for c in TagCategory}:
            raise ValueError(f"category must be one of {sorted(c.value for c in TagCategory)}")
        return value


class InteractionTagResponse(BaseModel):
    tag_id: uuid.UUID
    tag_name: str
    category: str
    sentiment: str
