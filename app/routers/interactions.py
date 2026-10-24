import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.interaction import InteractionCreate, InteractionResponse
from app.schemas.tag import InteractionTagAttach, InteractionTagResponse
from app.services.interaction_service import InteractionService
from app.services.tag_service import TagService

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


@router.post("/{interaction_id}/tags", response_model=InteractionTagResponse)
async def tag_interaction(
    interaction_id: uuid.UUID,
    data: InteractionTagAttach,
    user: User = Depends(get_or_create_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TagService(db)
    return await service.tag_interaction(user, interaction_id, data.tag_name, data.category, data.sentiment)


@router.get("/{interaction_id}/tags", response_model=list[InteractionTagResponse])
async def list_interaction_tags(interaction_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = TagService(db)
    return await service.list_tags(interaction_id)
