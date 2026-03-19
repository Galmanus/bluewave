"""Subscription and billing models.

Tracks tenant plan, Stripe integration, and billing period.
This is the skeleton — Stripe webhook handling comes later.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlanTier(str, enum.Enum):
    free = "free"
    pro = "pro"
    business = "business"
    enterprise = "enterprise"


# AI action limits per plan per month (0 = unlimited)
PLAN_AI_LIMITS = {
    PlanTier.free: 50,
    PlanTier.pro: 0,
    PlanTier.business: 0,
    PlanTier.enterprise: 0,
}

# Storage limits per plan in bytes
PLAN_STORAGE_LIMITS = {
    PlanTier.free: 5 * 1024 ** 3,        # 5 GB
    PlanTier.pro: 100 * 1024 ** 3,       # 100 GB
    PlanTier.business: 500 * 1024 ** 3,  # 500 GB
    PlanTier.enterprise: 0,              # unlimited
}

# Max users per plan (0 = unlimited)
PLAN_USER_LIMITS = {
    PlanTier.free: 3,
    PlanTier.pro: 0,
    PlanTier.business: 0,
    PlanTier.enterprise: 0,
}


class TenantSubscription(Base):
    __tablename__ = "tenant_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), unique=True, nullable=False
    )
    plan: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, name="plan_tier"), nullable=False, default=PlanTier.free
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_ai_actions_month: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    max_storage_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5 * 1024 ** 3
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
