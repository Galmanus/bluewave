"""AI usage tracking for metered billing.

Every AI action (caption generation, hashtag generation, compliance check, etc.)
is recorded here.  This powers:
  - Usage-based billing ($0.05/action, $0.25/brand-voice, etc.)
  - Analytics (AI usage trends per tenant)
  - Rate limiting (free tier caps)
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class AIActionType(str, enum.Enum):
    caption = "caption"
    hashtags = "hashtags"
    compliance_check = "compliance_check"
    auto_tag = "auto_tag"
    brand_voice = "brand_voice"
    content_brief = "content_brief"
    resize = "resize"


class AIUsageLog(TenantMixin, Base):
    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        Index("ix_ai_usage_tenant_created", "tenant_id", "created_at"),
        Index("ix_ai_usage_tenant_action", "tenant_id", "action_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[AIActionType] = mapped_column(
        Enum(AIActionType, name="ai_action_type"), nullable=False
    )
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_millicents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0,
        comment="Cost in 1/1000 of a cent for precise billing aggregation",
    )
    langsmith_run_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="LangSmith trace run ID for linking feedback to AI outputs",
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
