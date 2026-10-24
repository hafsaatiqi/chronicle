import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository

CLERK_API_BASE_URL = "https://api.clerk.com/v1"


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepository(db)

    async def get_or_create_by_clerk_id(self, clerk_id: str) -> User:
        existing = await self.user_repository.get_by_clerk_id(clerk_id)
        if existing is not None:
            return existing

        email, display_name = await self._fetch_clerk_profile(clerk_id)
        user = await self.user_repository.create(clerk_id=clerk_id, email=email, display_name=display_name)
        await self.db.commit()
        return user

    async def _fetch_clerk_profile(self, clerk_id: str) -> tuple[str, str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{CLERK_API_BASE_URL}/users/{clerk_id}",
                    headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
                )
                response.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not fetch user profile from Clerk",
            )

        data = response.json()
        email = self._extract_primary_email(data)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Clerk user has no resolvable email address",
            )

        first_name = data.get("first_name") or ""
        last_name = data.get("last_name") or ""
        display_name = f"{first_name} {last_name}".strip()

        return email, display_name

    def _extract_primary_email(self, data: dict) -> str | None:
        emails = data.get("email_addresses") or []
        primary_id = data.get("primary_email_address_id")
        for entry in emails:
            if entry.get("id") == primary_id:
                return entry.get("email_address")
        if emails:
            return emails[0].get("email_address")
        return None
