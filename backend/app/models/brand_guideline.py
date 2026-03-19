import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class BrandGuideline(TenantMixin, Base):
    """Stores a tenant's brand rules for AI compliance checking."""

    __tablename__ = "brand_guidelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    primary_colors: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    secondary_colors: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    fonts: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    logo_urls: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    tone_description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    dos: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    donts: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    custom_rules: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )
