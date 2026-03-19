import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_region: Mapped[str] = mapped_column(
        String(30), nullable=False, default="us-east-1", server_default="us-east-1"
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    assets = relationship(
        "MediaAsset", back_populates="tenant", cascade="all, delete-orphan"
    )
