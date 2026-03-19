"""Content briefs — AI-generated creative campaign briefs ($1.00 each)."""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.content_brief import BriefStatus, ContentBrief

router = APIRouter(prefix="/briefs", tags=["briefs"])


class BriefCreate(BaseModel):
    prompt: str


class BriefOut(BaseModel):
    id: uuid.UUID
    prompt: str
    brief_content: dict | None
    suggested_asset_ids: list[uuid.UUID] | None
    status: str
    cost_millicents: int
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[BriefOut])
async def list_briefs(
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(ContentBrief).order_by(ContentBrief.created_at.desc()).limit(50)
    )
    briefs = result.scalars().all()
    return [
        BriefOut(
            id=b.id, prompt=b.prompt, brief_content=b.brief_content,
            suggested_asset_ids=b.suggested_asset_ids, status=b.status.value,
            cost_millicents=b.cost_millicents, created_at=str(b.created_at),
        )
        for b in briefs
    ]


@router.get("/{brief_id}", response_model=BriefOut)
async def get_brief(
    brief_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(ContentBrief).where(ContentBrief.id == brief_id))
    brief = result.scalar_one_or_none()
    if not brief:
        raise HTTPException(404, "Brief not found")
    return BriefOut(
        id=brief.id, prompt=brief.prompt, brief_content=brief.brief_content,
        suggested_asset_ids=brief.suggested_asset_ids, status=brief.status.value,
        cost_millicents=brief.cost_millicents, created_at=str(brief.created_at),
    )


@router.post("", status_code=202)
async def create_brief(
    body: BriefCreate,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create a content brief. Generation runs in background (returns 202)."""
    brief = ContentBrief(
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
        prompt=body.prompt,
        status=BriefStatus.generating,
    )
    db.add(brief)
    await db.commit()
    await db.refresh(brief)

    from app.services.brief_service import generate_brief
    background_tasks.add_task(
        generate_brief, body.prompt, current_user.tenant_id, current_user.user_id, brief.id,
    )

    return {"id": str(brief.id), "status": "generating", "message": "Brief generation started"}
