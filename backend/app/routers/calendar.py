"""Content calendar — schedule posts for future publishing."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.asset import AssetStatus, MediaAsset
from app.models.scheduled_post import PostChannel, PostStatus, ScheduledPost

router = APIRouter(prefix="/calendar", tags=["calendar"])


class SchedulePostRequest(BaseModel):
    asset_id: uuid.UUID
    scheduled_at: datetime
    channel: PostChannel = PostChannel.manual
    caption_override: str | None = None
    hashtags_override: list[str] | None = None


class SchedulePostUpdate(BaseModel):
    scheduled_at: datetime | None = None
    channel: PostChannel | None = None
    caption_override: str | None = None
    hashtags_override: list[str] | None = None


class ScheduledPostOut(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    scheduled_at: datetime
    channel: str
    caption_override: str | None
    hashtags_override: list[str] | None
    status: str
    published_at: datetime | None
    external_url: str | None
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[ScheduledPostOut])
async def list_scheduled_posts(
    start: datetime = Query(...),
    end: datetime = Query(...),
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(ScheduledPost)
        .where(
            ScheduledPost.scheduled_at >= start,
            ScheduledPost.scheduled_at <= end,
        )
        .order_by(ScheduledPost.scheduled_at)
    )
    return result.scalars().all()


@router.post("", response_model=ScheduledPostOut, status_code=201)
async def create_scheduled_post(
    body: SchedulePostRequest,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    # Validate asset exists and is approved
    asset_result = await db.execute(select(MediaAsset).where(MediaAsset.id == body.asset_id))
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")
    if asset.status != AssetStatus.approved:
        raise HTTPException(400, "Only approved assets can be scheduled")
    if body.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(400, "scheduled_at must be in the future")

    post = ScheduledPost(
        tenant_id=current_user.tenant_id,
        asset_id=body.asset_id,
        scheduled_at=body.scheduled_at,
        channel=body.channel,
        caption_override=body.caption_override,
        hashtags_override=body.hashtags_override,
        created_by=current_user.user_id,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.patch("/{post_id}", response_model=ScheduledPostOut)
async def update_scheduled_post(
    post_id: uuid.UUID,
    body: SchedulePostUpdate,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(ScheduledPost).where(ScheduledPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Scheduled post not found")
    if post.status != PostStatus.scheduled:
        raise HTTPException(400, "Can only edit scheduled posts")

    if body.scheduled_at is not None:
        post.scheduled_at = body.scheduled_at
    if body.channel is not None:
        post.channel = body.channel
    if body.caption_override is not None:
        post.caption_override = body.caption_override
    if body.hashtags_override is not None:
        post.hashtags_override = body.hashtags_override

    await db.commit()
    await db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=204)
async def cancel_scheduled_post(
    post_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(ScheduledPost).where(ScheduledPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Scheduled post not found")
    if post.status != PostStatus.scheduled:
        raise HTTPException(400, "Can only cancel scheduled posts")

    post.status = PostStatus.cancelled
    await db.commit()
    return None


@router.post("/{post_id}/publish", response_model=ScheduledPostOut)
async def publish_post_manually(
    post_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(ScheduledPost).where(ScheduledPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(404, "Scheduled post not found")
    if post.status != PostStatus.scheduled:
        raise HTTPException(400, "Post is not in scheduled status")

    post.status = PostStatus.published
    post.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(post)
    return post
