"""Granular RBAC — manage resource-level permissions (admin only)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.permission import Permission, PermissionLevel, ResourceType

router = APIRouter(prefix="/permissions", tags=["permissions"])


class PermissionCreate(BaseModel):
    user_id: uuid.UUID
    resource_type: ResourceType
    resource_id: uuid.UUID | None = None
    permission: PermissionLevel


class PermissionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID | None
    permission: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[PermissionOut])
async def list_permissions(
    user_id: uuid.UUID | None = None,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    query = select(Permission)
    if user_id:
        query = query.where(Permission.user_id == user_id)
    result = await db.execute(query)
    return [
        PermissionOut(
            id=p.id, user_id=p.user_id, resource_type=p.resource_type.value,
            resource_id=p.resource_id, permission=p.permission.value,
            created_at=str(p.created_at),
        )
        for p in result.scalars().all()
    ]


@router.post("", response_model=PermissionOut, status_code=201)
async def create_permission(
    body: PermissionCreate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    perm = Permission(
        tenant_id=current_user.tenant_id,
        user_id=body.user_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        permission=body.permission,
        granted_by=current_user.user_id,
    )
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return PermissionOut(
        id=perm.id, user_id=perm.user_id, resource_type=perm.resource_type.value,
        resource_id=perm.resource_id, permission=perm.permission.value,
        created_at=str(perm.created_at),
    )


@router.delete("/{permission_id}", status_code=204)
async def delete_permission(
    permission_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(Permission).where(Permission.id == permission_id))
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(404, "Permission not found")
    await db.delete(perm)
    await db.commit()
    return None
