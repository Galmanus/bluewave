"""Plan limits enforcement — FastAPI dependencies that check tenant quotas.

Returns 402 Payment Required when a limit is exceeded.
Caches subscription data in memory for 5 minutes.
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, get_current_user
from app.core.tenant import get_tenant_db
from app.models.ai_usage import AIUsageLog
from app.models.asset import MediaAsset
from app.models.subscription import (
    PLAN_AI_LIMITS,
    PLAN_STORAGE_LIMITS,
    PLAN_USER_LIMITS,
    PlanTier,
    TenantSubscription,
)

logger = logging.getLogger("bluewave.plan_limits")

# Simple in-memory cache: {tenant_id: (subscription_dict, expires_at)}
_cache: dict[uuid.UUID, tuple[dict, float]] = {}
_CACHE_TTL = 300  # 5 minutes


async def _get_cached_limits(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Get subscription limits, cached for 5 minutes."""
    now = time.time()
    cached = _cache.get(tenant_id)
    if cached and cached[1] > now:
        return cached[0]

    result = await db.execute(
        select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
    )
    sub = result.scalar_one_or_none()

    if sub:
        limits = {
            "plan": sub.plan.value,
            "max_ai": sub.max_ai_actions_month,
            "max_storage": sub.max_storage_bytes,
            "max_users": sub.max_users,
        }
    else:
        limits = {
            "plan": "free",
            "max_ai": PLAN_AI_LIMITS[PlanTier.free],
            "max_storage": PLAN_STORAGE_LIMITS[PlanTier.free],
            "max_users": PLAN_USER_LIMITS[PlanTier.free],
        }

    _cache[tenant_id] = (limits, now + _CACHE_TTL)
    return limits


def invalidate_cache(tenant_id: uuid.UUID) -> None:
    """Call after subscription changes (e.g., Stripe webhook)."""
    _cache.pop(tenant_id, None)


async def check_ai_limit(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    """Dependency: check monthly AI action limit before AI operations."""
    limits = await _get_cached_limits(db, current_user.tenant_id)
    max_ai = limits["max_ai"]
    if max_ai == 0:
        return  # unlimited

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(AIUsageLog.id)).where(
            AIUsageLog.tenant_id == current_user.tenant_id,
            AIUsageLog.created_at >= month_start,
        )
    )
    count = result.scalar() or 0
    if count >= max_ai:
        raise HTTPException(
            status_code=402,
            detail="Monthly AI action limit reached. Upgrade your plan to continue.",
        )


async def check_storage_limit(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    """Dependency: check storage limit before uploads."""
    limits = await _get_cached_limits(db, current_user.tenant_id)
    max_storage = limits["max_storage"]
    if max_storage == 0:
        return  # unlimited

    result = await db.execute(
        select(func.coalesce(func.sum(MediaAsset.file_size), 0))
    )
    used = result.scalar() or 0
    if used >= max_storage:
        raise HTTPException(
            status_code=402,
            detail="Storage limit reached. Upgrade your plan to continue.",
        )


async def check_user_limit(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    """Dependency: check user seat limit before creating users."""
    limits = await _get_cached_limits(db, current_user.tenant_id)
    max_users = limits["max_users"]
    if max_users == 0:
        return  # unlimited

    from app.models.user import User
    result = await db.execute(select(func.count(User.id)))
    count = result.scalar() or 0
    if count >= max_users:
        raise HTTPException(
            status_code=402,
            detail="User seat limit reached. Upgrade your plan to add more users.",
        )
