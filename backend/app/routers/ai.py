import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, get_current_user, require_role
from app.core.plan_limits import check_ai_limit
from app.core.tenant import get_tenant_db
from app.models.asset import MediaAsset
from app.models.ai_usage import AIActionType, AIUsageLog
from app.schemas.asset import AssetOut
from app.services.ai_service import ai_service
from app.services.ai_usage import log_ai_usage

router = APIRouter(prefix="/ai", tags=["ai"])


class AIUsageSummary(BaseModel):
    period_start: datetime
    period_end: datetime
    total_actions: int
    actions_by_type: dict[str, int]
    total_cost_cents: float


@router.post("/caption/{asset_id}", response_model=AssetOut)
async def regenerate_caption(
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
    _limit: None = Depends(check_ai_limit),
):
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    filename = asset.file_path.rsplit("/", 1)[-1]
    asset.caption = await ai_service.generate_caption(
        filename, asset.file_type, file_path=asset.file_path
    )

    await log_ai_usage(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        asset_id=asset.id,
        action_type=AIActionType.caption,
    )

    await db.commit()
    await db.refresh(asset)
    return asset


@router.post("/hashtags/{asset_id}", response_model=AssetOut)
async def regenerate_hashtags(
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
    _limit: None = Depends(check_ai_limit),
):
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    filename = asset.file_path.rsplit("/", 1)[-1]
    asset.hashtags = await ai_service.generate_hashtags(
        filename, asset.file_type, file_path=asset.file_path
    )

    await log_ai_usage(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        asset_id=asset.id,
        action_type=AIActionType.hashtags,
    )

    await db.commit()
    await db.refresh(asset)
    return asset


@router.post("/caption/{asset_id}/translate")
async def translate_caption(
    asset_id: uuid.UUID,
    languages: str = Query("pt,es,fr", description="Comma-separated language codes"),
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
    _limit: None = Depends(check_ai_limit),
):
    """Generate captions in multiple languages for an asset."""
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    VALID_LANGS = {"en", "pt", "es", "fr", "de", "it", "nl", "ja", "ko", "zh", "ar", "ru", "hi", "pl", "sv", "da", "no", "fi"}
    lang_list = [l.strip().lower()[:5] for l in languages.split(",") if l.strip()]
    lang_list = [l for l in lang_list if l in VALID_LANGS]
    if not lang_list:
        raise HTTPException(400, "At least one valid language code required (e.g., en, pt, es)")

    filename = asset.file_path.rsplit("/", 1)[-1]
    captions = await ai_service.generate_caption_multilang(
        filename, asset.file_type, file_path=asset.file_path, languages=lang_list,
    )

    await log_ai_usage(
        db, tenant_id=current_user.tenant_id, user_id=current_user.user_id,
        asset_id=asset.id, action_type=AIActionType.caption,
    )

    await db.commit()
    return {"captions": captions, "languages": lang_list}


@router.get("/usage", response_model=AIUsageSummary)
async def get_ai_usage(
    days: int = Query(30, ge=1, le=365),
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get AI usage summary for the current tenant (admin only)."""
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)

    # Total actions
    total_result = await db.execute(
        select(func.count(AIUsageLog.id)).where(
            AIUsageLog.created_at >= period_start
        )
    )
    total_actions = total_result.scalar() or 0

    # Actions by type
    type_rows = await db.execute(
        select(AIUsageLog.action_type, func.count(AIUsageLog.id))
        .where(AIUsageLog.created_at >= period_start)
        .group_by(AIUsageLog.action_type)
    )
    actions_by_type = {row[0].value: row[1] for row in type_rows.all()}

    # Total cost
    cost_result = await db.execute(
        select(func.coalesce(func.sum(AIUsageLog.cost_millicents), 0)).where(
            AIUsageLog.created_at >= period_start
        )
    )
    total_millicents = cost_result.scalar() or 0

    return AIUsageSummary(
        period_start=period_start,
        period_end=now,
        total_actions=total_actions,
        actions_by_type=actions_by_type,
        total_cost_cents=total_millicents / 100_000,  # millicents → dollars
    )
