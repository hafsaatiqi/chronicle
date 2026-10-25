import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.enums import Medium
from app.schemas.work import WorkResponse
from app.services.work_service import WorkService

router = APIRouter(prefix="/works", tags=["works"])


@router.get("/search", response_model=list[WorkResponse])
async def search_works(
    q: str = Query(..., min_length=2),
    medium: Medium = Query(default=Medium.BOOK),
    db: AsyncSession = Depends(get_db),
):
    service = WorkService(db)
    results = await service.search_or_create(q, medium.value)
    return results


@router.get("/{work_id}", response_model=WorkResponse)
async def get_work(work_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = WorkService(db)
    return await service.get_work(work_id)
