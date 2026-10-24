import uuid

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str

    class Config:
        from_attributes = True
