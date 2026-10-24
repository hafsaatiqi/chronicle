from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.work import WorkResponse
from app.services.work_service import WorkService

router = APIRouter(prefix="/works", tags=["works"])


@router.get("/search", response_model=list[WorkResponse])
async def search_works(q: str = Query(..., min_length=2), db: AsyncSession = Depends(get_db)):
    service = WorkService(db)
    results = await service.search_or_create(q)
    return results
