"""Content briefs — AI-generated creative campaign briefs."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class BriefStatus(str, enum.Enum):
    generating = "generating"
    completed = "completed"
    failed = "failed"


class ContentBrief(TenantMixin, Base):
    __tablename__ = "content_briefs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    brief_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    suggested_asset_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    status: Mapped[BriefStatus] = mapped_column(Enum(BriefStatus, name="brief_status"), default=BriefStatus.generating, nullable=False)
    cost_millicents: Mapped[int] = mapped_column(BigInteger, default=100_000, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
