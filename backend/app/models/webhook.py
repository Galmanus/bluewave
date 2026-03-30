import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class WebhookEvent(str, enum.Enum):
    asset_uploaded = "asset.uploaded"
    asset_submitted = "asset.submitted"
    asset_approved = "asset.approved"
    asset_rejected = "asset.rejected"
    ai_completed = "ai.completed"
    user_invited = "user.invited"
    user_removed = "user.removed"
    payment_completed = "payment.completed"
    payment_failed = "payment.failed"
    subscription_activated = "subscription.activated"
    subscription_cancelled = "subscription.cancelled"


class Webhook(TenantMixin, Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    secret: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    events: Mapped[list[str]] = mapped_column(
        # Store as comma-separated or use ARRAY
        Text, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
