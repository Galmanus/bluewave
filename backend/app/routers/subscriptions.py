"""Subscription and billing endpoints.

Provides current plan info, usage stats, Stripe Checkout, Customer Portal,
webhook handling for payment events, and invoice listing.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import UserContext, get_current_user, require_role
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

logger = logging.getLogger("bluewave.billing")

router = APIRouter(prefix="/billing", tags=["billing"])


# -- Schemas ----------------------------------------------------------------

class PlanOut(BaseModel):
    plan: str
    is_active: bool
    max_users: int
    max_ai_actions_month: int
    max_storage_bytes: int
    current_period_start: datetime | None
    current_period_end: datetime | None
    stripe_customer_id: str | None


class UsageOut(BaseModel):
    ai_actions_used: int
    ai_actions_limit: int
    storage_used_bytes: int
    storage_limit_bytes: int
    users_count: int
    users_limit: int


class PlanSummaryOut(BaseModel):
    plan: PlanOut
    usage: UsageOut


class CheckoutRequest(BaseModel):
    target_plan: str  # pro, business, enterprise
    success_url: str
    cancel_url: str


class PortalRequest(BaseModel):
    return_url: str


# -- Helpers ----------------------------------------------------------------

async def _get_or_create_subscription(
    db: AsyncSession, tenant_id: uuid.UUID
) -> TenantSubscription:
    """Get existing subscription or create a free-tier default."""
    result = await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == tenant_id
        )
    )
    sub = result.scalar_one_or_none()
    if sub:
        return sub

    # Auto-provision free tier
    sub = TenantSubscription(
        tenant_id=tenant_id,
        plan=PlanTier.free,
        is_active=True,
        max_users=PLAN_USER_LIMITS[PlanTier.free],
        max_ai_actions_month=PLAN_AI_LIMITS[PlanTier.free],
        max_storage_bytes=PLAN_STORAGE_LIMITS[PlanTier.free],
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def _get_usage_stats(
    db: AsyncSession, tenant_id: uuid.UUID, sub: TenantSubscription
) -> UsageOut:
    """Compute current usage stats."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    ai_result = await db.execute(
        select(func.count(AIUsageLog.id)).where(
            AIUsageLog.tenant_id == tenant_id,
            AIUsageLog.created_at >= month_start,
        )
    )
    ai_used = ai_result.scalar() or 0

    storage_result = await db.execute(
        select(func.coalesce(func.sum(MediaAsset.file_size), 0))
    )
    storage_used = storage_result.scalar() or 0

    from app.models.user import User
    users_result = await db.execute(select(func.count(User.id)))
    users_count = users_result.scalar() or 0

    return UsageOut(
        ai_actions_used=ai_used,
        ai_actions_limit=sub.max_ai_actions_month,
        storage_used_bytes=storage_used,
        storage_limit_bytes=sub.max_storage_bytes,
        users_count=users_count,
        users_limit=sub.max_users,
    )


# -- Endpoints: Plan & Usage -----------------------------------------------

@router.get("/plan", response_model=PlanSummaryOut)
async def get_plan(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get current plan details and usage stats."""
    sub = await _get_or_create_subscription(db, current_user.tenant_id)
    usage = await _get_usage_stats(db, current_user.tenant_id, sub)

    return PlanSummaryOut(
        plan=PlanOut(
            plan=sub.plan.value,
            is_active=sub.is_active,
            max_users=sub.max_users,
            max_ai_actions_month=sub.max_ai_actions_month,
            max_storage_bytes=sub.max_storage_bytes,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            stripe_customer_id=sub.stripe_customer_id,
        ),
        usage=usage,
    )


@router.get("/usage", response_model=UsageOut)
async def get_usage(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get current usage stats only (lightweight)."""
    sub = await _get_or_create_subscription(db, current_user.tenant_id)
    return await _get_usage_stats(db, current_user.tenant_id, sub)


# -- Endpoints: Stripe Checkout & Portal ------------------------------------

@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a Stripe Checkout session for plan upgrade."""
    from app.services.stripe_service import (
        create_checkout_session,
        create_customer,
        get_price_ids,
        init_stripe,
    )

    if not init_stripe():
        raise HTTPException(503, "Billing not configured")

    price_ids = get_price_ids()
    price_id = price_ids.get(body.target_plan)
    if not price_id:
        raise HTTPException(400, f"Unknown plan: {body.target_plan}. Available: {list(price_ids.keys())}")

    sub = await _get_or_create_subscription(db, current_user.tenant_id)

    # Ensure tenant has a Stripe customer
    if not sub.stripe_customer_id:
        from app.models.user import User
        user_result = await db.execute(select(User).where(User.id == current_user.user_id))
        user = user_result.scalar_one()
        customer = await create_customer(current_user.tenant_id, user.email, user.full_name)
        sub.stripe_customer_id = customer.id
        await db.commit()

    url = await create_checkout_session(
        sub.stripe_customer_id, price_id, body.success_url, body.cancel_url
    )
    return {"url": url}


@router.post("/portal")
async def create_portal(
    body: PortalRequest,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a Stripe Customer Portal session."""
    from app.services.stripe_service import create_portal_session, init_stripe

    if not init_stripe():
        raise HTTPException(503, "Billing not configured")

    sub = await _get_or_create_subscription(db, current_user.tenant_id)
    if not sub.stripe_customer_id:
        raise HTTPException(400, "No active Stripe subscription. Please upgrade first.")

    url = await create_portal_session(sub.stripe_customer_id, body.return_url)
    return {"url": url}


@router.get("/invoices")
async def list_invoices(
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List Stripe invoices for the tenant."""
    from app.services.stripe_service import init_stripe
    from app.services.stripe_service import list_invoices as stripe_list_invoices

    if not init_stripe():
        raise HTTPException(503, "Billing not configured")

    sub = await _get_or_create_subscription(db, current_user.tenant_id)
    if not sub.stripe_customer_id:
        return []

    return await stripe_list_invoices(sub.stripe_customer_id)


# -- Endpoints: Stripe Webhooks --------------------------------------------

@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events. No JWT auth — validated via Stripe signature."""
    from app.services.stripe_service import construct_webhook_event, init_stripe

    if not init_stripe():
        raise HTTPException(503, "Billing not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = construct_webhook_event(payload, sig_header)
    except Exception:
        logger.warning("Invalid Stripe webhook signature")
        raise HTTPException(400, "Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe webhook: %s", event_type)

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if customer_id and subscription_id:
            result = await db.execute(
                select(TenantSubscription).where(
                    TenantSubscription.stripe_customer_id == customer_id
                )
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.stripe_subscription_id = subscription_id
                sub.is_active = True
                # Determine plan from metadata or default to pro
                sub.plan = PlanTier.pro
                sub.max_users = PLAN_USER_LIMITS[PlanTier.pro]
                sub.max_ai_actions_month = PLAN_AI_LIMITS[PlanTier.pro]
                sub.max_storage_bytes = PLAN_STORAGE_LIMITS[PlanTier.pro]
                await db.commit()
                logger.info("Subscription activated for customer %s", customer_id)

    elif event_type == "customer.subscription.updated":
        subscription_id = data.get("id")
        status = data.get("status")
        if subscription_id:
            result = await db.execute(
                select(TenantSubscription).where(
                    TenantSubscription.stripe_subscription_id == subscription_id
                )
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.is_active = status == "active"
                if data.get("current_period_start"):
                    sub.current_period_start = datetime.fromtimestamp(
                        data["current_period_start"], tz=timezone.utc
                    )
                if data.get("current_period_end"):
                    sub.current_period_end = datetime.fromtimestamp(
                        data["current_period_end"], tz=timezone.utc
                    )
                await db.commit()

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        if subscription_id:
            result = await db.execute(
                select(TenantSubscription).where(
                    TenantSubscription.stripe_subscription_id == subscription_id
                )
            )
            sub = result.scalar_one_or_none()
            if sub:
                # Downgrade to free
                sub.plan = PlanTier.free
                sub.is_active = True
                sub.stripe_subscription_id = None
                sub.max_users = PLAN_USER_LIMITS[PlanTier.free]
                sub.max_ai_actions_month = PLAN_AI_LIMITS[PlanTier.free]
                sub.max_storage_bytes = PLAN_STORAGE_LIMITS[PlanTier.free]
                await db.commit()
                logger.info("Subscription cancelled — downgraded to free")

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        if customer_id:
            result = await db.execute(
                select(TenantSubscription).where(
                    TenantSubscription.stripe_customer_id == customer_id
                )
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.is_active = False
                await db.commit()
                logger.warning("Payment failed for customer %s", customer_id)

    return {"received": True}
