import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_key_auth import generate_api_key
from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.api_key import APIKey

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class APIKeyCreate(BaseModel):
    name: str


class APIKeyCreated(BaseModel):
    id: uuid.UUID
    name: str
    key: str
    key_prefix: str
    message: str = "Save this key — it won't be shown again."

    model_config = {"from_attributes": True}


class APIKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[APIKeyOut])
async def list_api_keys(
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(APIKey))
    return result.scalars().all()


@router.post("", response_model=APIKeyCreated, status_code=201)
async def create_api_key(
    body: APIKeyCreate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    full_key, key_hash, key_prefix = generate_api_key()

    api_key = APIKey(
        tenant_id=current_user.tenant_id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        created_by=current_user.user_id,
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key=full_key,
        key_prefix=key_prefix,
    )


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    await db.commit()
    return None
