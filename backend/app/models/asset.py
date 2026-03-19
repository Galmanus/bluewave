import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin


class AssetStatus(str, enum.Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"


class MediaAsset(TenantMixin, TimestampMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        Index("ix_media_assets_tenant_id_id", "tenant_id", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status"),
        nullable=False,
        default=AssetStatus.draft,
    )
    rejection_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compliance_issues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    tenant = relationship("Tenant", back_populates="assets")
    uploaded_by_user = relationship("User", back_populates="assets")
