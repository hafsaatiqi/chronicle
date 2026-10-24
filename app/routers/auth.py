from fastapi import APIRouter, Depends

from app.core.auth import get_or_create_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def whoami(user: User = Depends(get_or_create_current_user)):
    return user
