"""AI action rate limiting by tenant plan.

Checks ai_usage_logs count for current calendar month against plan limits.
Free: 50/month, Pro: unlimited, Business: unlimited, Enterprise: unlimited.
Also enforces daily upload limits and per-minute API rate limits.
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_usage import AIUsageLog

# Plan-based limits (-1 = unlimited)
PLAN_LIMITS: dict[str, dict[str, int]] = {
    "free": {"ai_actions_per_month": 50, "uploads_per_day": 10, "api_requests_per_minute": 30},
    "pro": {"ai_actions_per_month": -1, "uploads_per_day": 100, "api_requests_per_minute": 120},
    "business": {"ai_actions_per_month": -1, "uploads_per_day": 500, "api_requests_per_minute": 300},
    "enterprise": {"ai_actions_per_month": -1, "uploads_per_day": -1, "api_requests_per_minute": 1000},
}


async def _get_tenant_plan(db: AsyncSession, tenant_id: uuid.UUID) -> str:
    """Resolve the current plan tier for a tenant."""
    try:
        from app.models.subscription import TenantSubscription
        result = await db.execute(
            select(TenantSubscription.plan_tier)
            .where(
                TenantSubscription.tenant_id == tenant_id,
                TenantSubscription.is_active.is_(True),
            )
        )
        tier = result.scalar_one_or_none()
        return tier.value if tier else "free"
    except Exception:
        return "free"


async def check_ai_rate_limit(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int | None = None,
) -> None:
    """Raise 402 if tenant has exceeded their monthly AI action limit.

    Args:
        db: Database session (tenant-scoped).
        tenant_id: Tenant UUID.
        limit: Override limit. If None, resolves from plan.
               Pass 0 for unlimited.
    """
    if limit is not None:
        max_actions = limit
    else:
        plan = await _get_tenant_plan(db, tenant_id)
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
        max_actions = limits["ai_actions_per_month"]

    if max_actions == -1 or max_actions == 0:
        return  # unlimited

    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(AIUsageLog.id)).where(
            AIUsageLog.tenant_id == tenant_id,
            AIUsageLog.created_at >= month_start,
        )
    )
    count = result.scalar() or 0

    if count >= max_actions:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "AI action limit reached",
                "current": count,
                "limit": max_actions,
                "upgrade_url": "/billing",
                "message": f"Monthly AI action limit reached ({max_actions} actions). Upgrade your plan for more.",
            },
        )


async def check_upload_rate_limit(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> None:
    """Raise 429 if tenant exceeded daily upload limit."""
    plan = await _get_tenant_plan(db, tenant_id)
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    max_uploads = limits["uploads_per_day"]

    if max_uploads == -1:
        return

    from app.models.asset import MediaAsset

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(MediaAsset.id)).where(
            MediaAsset.tenant_id == tenant_id,
            MediaAsset.created_at >= today_start,
        )
    )
    count = result.scalar() or 0

    if count >= max_uploads:
        raise HTTPException(
            status_code=429,
            detail=f"Daily upload limit reached ({max_uploads} uploads/day). Upgrade for more.",
        )
