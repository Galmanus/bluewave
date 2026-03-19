"""Audit log endpoint — admin-only, paginated, filterable."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditLogOut(BaseModel):
    id: str
    user_id: str
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    size: int


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List audit logs (admin only, paginated, filterable by action)."""
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    items = result.scalars().all()

    return AuditLogListResponse(items=items, total=total, page=page, size=size)
