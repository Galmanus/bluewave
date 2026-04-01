"""Asset comments — collaborative review discussion threads."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import UserContext, get_current_user, require_role
from app.core.tenant import get_tenant_db
from app.models.comment import AssetComment
from app.models.user import User

router = APIRouter(prefix="/assets/{asset_id}/comments", tags=["comments"])


class CommentCreate(BaseModel):
    body: str
    parent_id: uuid.UUID | None = None


class CommentUpdate(BaseModel):
    body: str


class CommentOut(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    user_id: uuid.UUID
    parent_id: uuid.UUID | None
    body: str
    is_resolved: bool
    created_at: str
    updated_at: str
    user_name: str | None = None

    class Config:
        from_attributes = True


@router.get("", response_model=list[CommentOut])
async def list_comments(
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List comments for an asset, ordered by creation time.

    Uses a single query with JOIN to avoid N+1 user lookups.
    """
    result = await db.execute(
        select(AssetComment, User.full_name)
        .outerjoin(User, AssetComment.user_id == User.id)
        .where(AssetComment.asset_id == asset_id)
        .order_by(AssetComment.created_at)
    )
    rows = result.all()

    return [
        CommentOut(
            id=c.id,
            asset_id=c.asset_id,
            user_id=c.user_id,
            parent_id=c.parent_id,
            body=c.body,
            is_resolved=c.is_resolved,
            created_at=str(c.created_at),
            updated_at=str(c.updated_at),
            user_name=user_name,
        )
        for c, user_name in rows
    ]


@router.post("", response_model=CommentOut, status_code=201)
async def create_comment(
    asset_id: uuid.UUID,
    body: CommentCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    comment = AssetComment(
        tenant_id=current_user.tenant_id,
        asset_id=asset_id,
        user_id=current_user.user_id,
        parent_id=body.parent_id,
        body=body.body,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    user_result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = user_result.scalar_one_or_none()

    return CommentOut(
        id=comment.id,
        asset_id=comment.asset_id,
        user_id=comment.user_id,
        parent_id=comment.parent_id,
        body=comment.body,
        is_resolved=comment.is_resolved,
        created_at=str(comment.created_at),
        updated_at=str(comment.updated_at),
        user_name=user.full_name if user else None,
    )


@router.patch("/{comment_id}", response_model=CommentOut)
async def update_comment(
    asset_id: uuid.UUID,
    comment_id: uuid.UUID,
    body: CommentUpdate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(AssetComment).where(AssetComment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(404, "Comment not found")
    if comment.user_id != current_user.user_id:
        raise HTTPException(403, "Can only edit your own comments")

    comment.body = body.body
    await db.commit()
    await db.refresh(comment)
    return CommentOut(
        id=comment.id, asset_id=comment.asset_id, user_id=comment.user_id,
        parent_id=comment.parent_id, body=comment.body, is_resolved=comment.is_resolved,
        created_at=str(comment.created_at), updated_at=str(comment.updated_at),
    )


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    asset_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(AssetComment).where(AssetComment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(404, "Comment not found")
    if comment.user_id != current_user.user_id and current_user.role != "admin":
        raise HTTPException(403, "Can only delete your own comments")

    await db.delete(comment)
    await db.commit()
    return None


@router.post("/{comment_id}/resolve", status_code=200)
async def resolve_comment(
    asset_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(AssetComment).where(AssetComment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(404, "Comment not found")

    comment.is_resolved = True
    await db.commit()
    return {"message": "Comment resolved"}
