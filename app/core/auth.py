import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.user import User
from app.services.user_service import UserService

_security = HTTPBearer()
_jwks_client = PyJWKClient(f"{settings.clerk_issuer}/.well-known/jwks.json")


def get_current_clerk_id(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> str:
    token = credentials.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    clerk_id = payload.get("sub")
    if not clerk_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject claim")

    return clerk_id


async def get_or_create_current_user(
    clerk_id: str = Depends(get_current_clerk_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_service = UserService(db)
    return await user_service.get_or_create_by_clerk_id(clerk_id)
