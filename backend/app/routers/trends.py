import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, get_current_user, require_role
from app.core.tenant import get_tenant_db
from app.models.trend import TrendEntry, TrendSource
from app.services.trend_service import discover_trends

router = APIRouter(prefix="/trends", tags=["trends"])


# --- Schemas ---

class TrendOut(BaseModel):
    id: uuid.UUID
    keyword: str
    source: str
    volume: int
    volume_change_pct: float
    sentiment_score: float | None
    region: str
    category: str | None
    relevance_score: float
    ai_suggestion: str | None
    ai_caption_draft: str | None
    ai_hashtags: list | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrendDiscoverRequest(BaseModel):
    keywords: list[str] | None = None
    region: str = "US"
    niche: str = "marketing and creative content"


class TrendDiscoverResponse(BaseModel):
    discovered: int
    trends: list[TrendOut]


# --- Background task ---

async def _discover_and_store(
    tenant_id: uuid.UUID,
    keywords: list[str] | None,
    region: str,
    niche: str,
):
    """Background: fetch trends, analyze with AI, store results."""
    from app.core.database import async_session_factory

    results = await discover_trends(
        keywords=keywords,
        region=region,
        tenant_niche=niche,
    )

    if not results:
        return

    async with async_session_factory() as db:
        for item in results:
            entry = TrendEntry(
                tenant_id=tenant_id,
                keyword=item["keyword"],
                source=TrendSource(item.get("source", "combined")),
                volume=item.get("volume", 0),
                volume_change_pct=item.get("volume_change_pct", 0.0),
                sentiment_score=item.get("sentiment_score"),
                region=item.get("region", region),
                category=item.get("category"),
                raw_data=item.get("raw_data"),
                relevance_score=item.get("relevance_score", 0.0),
                ai_suggestion=item.get("ai_suggestion"),
                ai_caption_draft=item.get("ai_caption_draft"),
                ai_hashtags=item.get("ai_hashtags"),
                expires_at=datetime.now(timezone.utc) + timedelta(
                    hours=item.get("urgency_hours", 24)
                ),
            )
            db.add(entry)
        await db.commit()


# --- Endpoints ---

@router.post("/discover", response_model=TrendDiscoverResponse)
async def discover(
    body: TrendDiscoverRequest,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Trigger trend discovery from Google Trends + X/Twitter.

    Fetches trends, analyzes with Claude AI, and stores results.
    Returns immediately with existing trends while discovery runs in background.
    """
    # Fire background discovery
    background_tasks.add_task(
        _discover_and_store,
        current_user.tenant_id,
        body.keywords,
        body.region,
        body.niche,
    )

    # Return existing trends while new ones are being discovered
    result = await db.execute(
        select(TrendEntry)
        .order_by(desc(TrendEntry.relevance_score))
        .limit(20)
    )
    existing = result.scalars().all()

    return TrendDiscoverResponse(
        discovered=len(existing),
        trends=existing,
    )


@router.get("", response_model=list[TrendOut])
async def list_trends(
    active_only: bool = Query(True, description="Only show non-expired trends"),
    limit: int = Query(20, ge=1, le=50),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List discovered trends for the tenant, ordered by relevance."""
    query = select(TrendEntry).order_by(desc(TrendEntry.relevance_score))

    if active_only:
        query = query.where(
            (TrendEntry.expires_at.is_(None))
            | (TrendEntry.expires_at > datetime.now(timezone.utc))
        )

    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{trend_id}", response_model=TrendOut)
async def get_trend(
    trend_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get a single trend entry with AI suggestions."""
    result = await db.execute(
        select(TrendEntry).where(TrendEntry.id == trend_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Trend not found")
    return entry


@router.delete("/expired", status_code=204)
async def cleanup_expired(
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Remove expired trend entries."""
    await db.execute(
        delete(TrendEntry).where(
            TrendEntry.expires_at < datetime.now(timezone.utc)
        )
    )
    await db.commit()
    return None
