"""API Key authentication for external integrations (OpenClaw, Zapier, etc).

API keys are passed via X-API-Key header. They provide the same tenant
context as JWT but without session management.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import UserContext
from app.models.api_key import APIKey
from app.models.user import User

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(key: str) -> str:
    """Hash an API key for storage (SHA-256)."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key. Returns (full_key, key_hash, key_prefix)."""
    raw = secrets.token_urlsafe(32)
    full_key = f"bw_{raw}"
    return full_key, hash_api_key(full_key), full_key[:8]


async def get_current_user_or_api_key(
    api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> UserContext | None:
    """Resolve API key to UserContext. Returns None if no key provided
    (allows fallback to JWT auth in combined dependency)."""
    if not api_key:
        return None

    key_hash = hash_api_key(api_key)
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
    )
    api_key_record = result.scalar_one_or_none()
    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Update last_used_at
    await db.execute(
        update(APIKey)
        .where(APIKey.id == api_key_record.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()

    # Get the user who created this key to inherit their role
    user_result = await db.execute(
        select(User).where(User.id == api_key_record.created_by)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="API key owner not found")

    return UserContext(
        user_id=user.id,
        tenant_id=api_key_record.tenant_id,
        role=user.role.value,
    )
