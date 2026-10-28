import uuid

from fastapi import APIRouter, Depends, Query, Response, status as http_status
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
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_or_create_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InteractionService(db)
    return await service.list_my_shelf(user, status, limit, offset)


@router.delete("/{interaction_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_interaction(
    interaction_id: uuid.UUID,
    user: User = Depends(get_or_create_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = InteractionService(db)
    await service.delete_interaction(user, interaction_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


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


@router.delete("/{interaction_id}/tags/{tag_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def remove_interaction_tag(
    interaction_id: uuid.UUID,
    tag_id: uuid.UUID,
    user: User = Depends(get_or_create_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TagService(db)
    await service.remove_tag(user, interaction_id, tag_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
