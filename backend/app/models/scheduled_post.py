"""Scheduled posts for the content calendar."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin


class PostChannel(str, enum.Enum):
    instagram = "instagram"
    facebook = "facebook"
    twitter = "twitter"
    linkedin = "linkedin"
    tiktok = "tiktok"
    manual = "manual"


class PostStatus(str, enum.Enum):
    scheduled = "scheduled"
    published = "published"
    failed = "failed"
    cancelled = "cancelled"


class ScheduledPost(TenantMixin, Base):
    __tablename__ = "scheduled_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    channel: Mapped[PostChannel] = mapped_column(Enum(PostChannel, name="post_channel"), nullable=False, default=PostChannel.manual)
    caption_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags_override: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    status: Mapped[PostStatus] = mapped_column(Enum(PostStatus, name="post_status"), default=PostStatus.scheduled, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)

    asset = relationship("MediaAsset", lazy="joined")
