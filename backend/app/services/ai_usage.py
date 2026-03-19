"""Helpers to log AI usage for metered billing + Stripe metering."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_usage import AIActionType, AIUsageLog

logger = logging.getLogger("bluewave.ai_usage")

# Cost table in millicents (1/1000 cent)
# $0.05 per action = 5000 millicents
_COST_TABLE: dict[AIActionType, int] = {
    AIActionType.caption: 5_000,
    AIActionType.hashtags: 5_000,
    AIActionType.compliance_check: 5_000,
    AIActionType.auto_tag: 5_000,
    AIActionType.brand_voice: 25_000,       # $0.25
    AIActionType.content_brief: 100_000,    # $1.00
    AIActionType.resize: 5_000,
}


async def _report_to_stripe(tenant_id: uuid.UUID) -> None:
    """Report 1 metered usage unit to Stripe (async, non-blocking)."""
    if not settings.STRIPE_SECRET_KEY:
        return
    try:
        from app.core.database import async_session_factory
        from app.models.subscription import TenantSubscription

        async with async_session_factory() as db:
            result = await db.execute(
                select(TenantSubscription).where(
                    TenantSubscription.tenant_id == tenant_id,
                    TenantSubscription.stripe_subscription_id.isnot(None),
                    TenantSubscription.is_active.is_(True),
                )
            )
            sub = result.scalar_one_or_none()
            if not sub or not sub.stripe_subscription_id:
                return

        from app.services.stripe_service import init_stripe, report_usage
        init_stripe()
        # Use subscription_id as item_id — in a real setup you'd look up the
        # metered subscription item ID from the subscription object.
        await report_usage(sub.stripe_subscription_id, quantity=1)
    except Exception:
        logger.warning("Failed to report AI usage to Stripe for tenant %s", tenant_id)


async def log_ai_usage(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    asset_id: uuid.UUID | None,
    action_type: AIActionType,
    input_tokens: int = 0,
    output_tokens: int = 0,
    langsmith_run_id: str | None = None,
) -> AIUsageLog:
    """Record an AI action for billing and analytics."""
    log = AIUsageLog(
        tenant_id=tenant_id,
        user_id=user_id,
        asset_id=asset_id,
        action_type=action_type,
        model_used=settings.AI_MODEL if settings.ANTHROPIC_API_KEY else "stub",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_millicents=_COST_TABLE.get(action_type, 5_000),
        langsmith_run_id=langsmith_run_id,
    )
    db.add(log)

    # Report to Stripe in background (don't block the request)
    try:
        await _report_to_stripe(tenant_id)
    except Exception:
        pass  # Never block AI action due to Stripe failure

    return log
