from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.interaction import InteractionCreate, InteractionResponse
from app.services.interaction_service import InteractionService

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=InteractionResponse)
async def log_interaction(
    data: InteractionCreate,
    user: User = Depends(get_or_create_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InteractionService(db)
    return await service.log_interaction(user, data)


@router.get("/me", response_model=list[InteractionResponse])
async def list_my_interactions(
    status: str | None = Query(default=None),
    user: User = Depends(get_or_create_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InteractionService(db)
    return await service.list_my_shelf(user, status)
