from fastapi import APIRouter, Depends

from app.core.auth import get_current_clerk_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def whoami(clerk_id: str = Depends(get_current_clerk_id)):
    return {"clerk_id": clerk_id}
