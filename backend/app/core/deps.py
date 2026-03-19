import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class UserContext:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserContext:
    """Authenticate via JWT Bearer token OR X-API-Key header."""

    # 1. Try JWT Bearer first
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload is not None and payload.get("type") == "access":
            return UserContext(
                user_id=uuid.UUID(payload["sub"]),
                tenant_id=uuid.UUID(payload["tenant_id"]),
                role=payload["role"],
            )

    # 2. Try X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        from app.models.api_key import APIKey
        from app.models.user import User

        key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        result = await db.execute(
            select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
        )
        api_key_record = result.scalar_one_or_none()
        if api_key_record:
            # Update last_used_at
            await db.execute(
                update(APIKey)
                .where(APIKey.id == api_key_record.id)
                .values(last_used_at=datetime.now(timezone.utc))
            )
            await db.commit()

            # Get the creator's role
            user_result = await db.execute(
                select(User).where(User.id == api_key_record.created_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                return UserContext(
                    user_id=user.id,
                    tenant_id=api_key_record.tenant_id,
                    role=user.role.value,
                )

    # 3. No valid auth found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication",
    )


def require_role(*allowed_roles: str):
    def dependency(current_user: UserContext = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return dependency
