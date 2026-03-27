"""Trackeer — Self-hosted event tracking & tag management models.

Equivalent to Google Tag Manager + Segment, but self-hosted and LGPD-compliant.
IPs are hashed before storage. No PII stored in events.
"""

import hashlib
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TrackeerSite(Base):
    """A registered site/property that embeds the Trackeer snippet."""

    __tablename__ = "trackeer_sites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(500), nullable=False)
    site_key: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True,
        default=lambda: uuid.uuid4().hex
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    tags = relationship("TrackeerTag", back_populates="site", cascade="all, delete-orphan")
    events = relationship("TrackeerEvent", back_populates="site", cascade="all, delete-orphan")


class TrackeerTag(Base):
    """A tag/trigger configuration — defines WHAT to track and WHEN.

    trigger_type options:
      - pageview     : fires on page load, optionally filtered by url_pattern
      - click        : fires when a CSS selector is clicked
      - form_submit  : fires on form submission
      - scroll_depth : fires when user scrolls past a % threshold
      - custom       : fired explicitly via window.__trk.track()

    trigger_config examples:
      pageview     : {"url_pattern": "/checkout"}          -- regex or null for all pages
      click        : {"selector": "#btn-comprar"}
      form_submit  : {"selector": "form.lead-form"}
      scroll_depth : {"threshold": 75}                     -- fires at 75% scroll
      custom       : {}                                    -- relies on manual __trk.track()

    custom_script: optional JS code executed when the tag fires.
    Runs in the page context. Use to push to dataLayer, fire pixels, etc.
    """

    __tablename__ = "trackeer_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trackeer_sites.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    custom_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    site = relationship("TrackeerSite", back_populates="tags")

    __table_args__ = (
        Index("ix_trackeer_tags_site_enabled", "site_id", "enabled"),
    )


class TrackeerEvent(Base):
    """A single tracked event. High-volume time-series table.

    Design decisions for LGPD compliance:
    - IP is SHA-256 hashed (one-way, cannot recover original)
    - No name, email, or other PII stored
    - session_id is anonymous (localStorage-generated random string)
    - user_agent stored for device analytics but not linked to any identity
    """

    __tablename__ = "trackeer_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trackeer_sites.id"), nullable=False, index=True
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, index=True
    )

    site = relationship("TrackeerSite", back_populates="events")

    __table_args__ = (
        Index("ix_trackeer_events_site_event_ts", "site_id", "event_name", "timestamp"),
        Index("ix_trackeer_events_session_ts", "session_id", "timestamp"),
    )

    @staticmethod
    def hash_ip(ip: str) -> str:
        return hashlib.sha256(ip.encode()).hexdigest()[:32]
