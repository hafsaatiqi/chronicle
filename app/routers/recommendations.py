from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_or_create_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationResponse])
async def get_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    user: User = Depends(get_or_create_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RecommendationService(db)
    return await service.get_recommendations(user, limit)
