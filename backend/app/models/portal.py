import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin


class ClientPortal(TenantMixin, Base):
    __tablename__ = "client_portals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#2563EB")
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    collections = relationship("PortalCollection", back_populates="portal", cascade="all, delete-orphan")


class PortalCollection(TenantMixin, Base):
    __tablename__ = "portal_collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("client_portals.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    portal = relationship("ClientPortal", back_populates="collections")
    assets = relationship("PortalCollectionAsset", back_populates="collection", cascade="all, delete-orphan")


class PortalCollectionAsset(Base):
    __tablename__ = "portal_collection_assets"

    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portal_collections.id"), primary_key=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("media_assets.id"), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    collection = relationship("PortalCollection", back_populates="assets")
