import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class TrendSource(str, enum.Enum):
    google_trends = "google_trends"
    x_twitter = "x_twitter"
    combined = "combined"


class TrendEntry(TenantMixin, Base):
    """Stores discovered trending topics with relevance scoring."""

    __tablename__ = "trend_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[TrendSource] = mapped_column(
        Enum(TrendSource, name="trend_source"), nullable=False
    )
    volume: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    volume_change_pct: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    sentiment_score: Mapped[float] = mapped_column(
        Float, nullable=True
    )
    region: Mapped[str] = mapped_column(
        String(10), nullable=False, default="US"
    )
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    raw_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    ai_suggestion: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    ai_caption_draft: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    ai_hashtags: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True
    )
    relevance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
