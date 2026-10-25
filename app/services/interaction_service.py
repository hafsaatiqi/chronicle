from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InteractionStatus
from app.models.user import User
from app.models.user_interaction import UserInteraction
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.work_repository import WorkRepository
from app.schemas.interaction import InteractionCreate

_RATING_ALLOWED_STATUSES = {InteractionStatus.FINISHED.value, InteractionStatus.DROPPED.value}
_VALID_STATUSES = {s.value for s in InteractionStatus}


class InteractionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.interaction_repository = InteractionRepository(db)
        self.work_repository = WorkRepository(db)

    async def log_interaction(self, user: User, data: InteractionCreate) -> UserInteraction:
        work = await self.work_repository.get_by_id(data.work_id)
        if work is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work not found")

        effective_status = self._resolve_status(data.status, data.rating)

        existing = await self.interaction_repository.get_by_user_and_work(user.id, data.work_id)
        if existing is not None:
            result = await self.interaction_repository.update(
                existing, status=effective_status, rating=data.rating, review_text=data.review_text
            )
        else:
            result = await self.interaction_repository.create(
                user.id, data.work_id, effective_status, data.rating, data.review_text
            )

        await self.db.commit()
        return result

    async def list_my_shelf(self, user: User, status_filter: str | None) -> list[UserInteraction]:
        if status_filter is not None and status_filter not in _VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid status filter '{status_filter}'",
            )
        return await self.interaction_repository.list_by_user(user.id, status_filter)

    def _resolve_status(self, status_value: str | None, rating: int | None) -> str:
        if status_value is None:
            if rating is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="status is required when rating is not provided",
                )
            return InteractionStatus.FINISHED.value

        if status_value not in _VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid status '{status_value}'",
            )

        if rating is not None and status_value not in _RATING_ALLOWED_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="rating is only allowed when status is FINISHED or DROPPED",
            )

        return status_value
