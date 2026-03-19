"""Analytics endpoints — SQL aggregations for dashboard KPIs, trends, team stats, and ROI.

All queries use SQL aggregation (never loads individual rows into Python).
Results are cached in Redis for 5 minutes.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import case, cast, Float, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.ai_usage import AIUsageLog
from app.models.asset import AssetStatus, MediaAsset
from app.models.user import User

logger = logging.getLogger("bluewave.analytics")

router = APIRouter(prefix="/analytics", tags=["analytics"])

CACHE_TTL = 300  # 5 minutes


# -- Schemas ----------------------------------------------------------------

class OverviewOut(BaseModel):
    total_assets: int
    total_approved: int
    total_rejected: int
    avg_approval_time_hours: float | None
    ai_actions_count: int
    ai_cost_cents: float
    compliance_avg_score: float | None
    assets_by_status: dict[str, int]


class TrendPoint(BaseModel):
    period: str
    uploads: int
    approvals: int
    rejections: int
    ai_actions: int
    avg_compliance: float | None


class TeamMember(BaseModel):
    user_id: str
    full_name: str
    uploads: int
    approvals: int


class AIUsageDetail(BaseModel):
    actions_by_type: dict[str, int]
    total_cost_cents: float
    avg_cost_per_asset_cents: float


class AIQualityMetrics(BaseModel):
    caption_quality: dict
    hashtags_quality: dict
    compliance_quality: dict


class ROIOut(BaseModel):
    estimated_hours_saved: float
    estimated_cost_saved_usd: float
    assets_processed: int
    avg_time_to_approval_hours: float | None


# -- Helpers ----------------------------------------------------------------

def _cache_key(tenant_id, endpoint: str, days: int) -> str:
    return f"analytics:{tenant_id}:{endpoint}:{days}"


# -- Endpoints --------------------------------------------------------------

@router.get("/overview", response_model=OverviewOut)
async def get_overview(
    days: int = Query(30, ge=1, le=365),
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Overview KPIs for the dashboard."""
    key = _cache_key(current_user.tenant_id, "overview", days)
    cached = await cache_get(key)
    if cached:
        return OverviewOut(**cached)

    since = datetime.utcnow() - timedelta(days=days)

    # Asset stats
    asset_result = await db.execute(
        select(
            func.count(MediaAsset.id).label("total"),
            func.count(case((MediaAsset.status == AssetStatus.approved, 1))).label("approved"),
            func.avg(
                case(
                    (MediaAsset.compliance_score.isnot(None), cast(MediaAsset.compliance_score, Float)),
                )
            ).label("avg_compliance"),
        ).where(MediaAsset.created_at >= since)
    )
    row = asset_result.one()
    total_assets = row.total or 0
    total_approved = row.approved or 0
    avg_compliance = round(float(row.avg_compliance), 1) if row.avg_compliance else None

    # Status breakdown
    status_result = await db.execute(
        select(MediaAsset.status, func.count(MediaAsset.id))
        .where(MediaAsset.created_at >= since)
        .group_by(MediaAsset.status)
    )
    assets_by_status = {r[0].value: r[1] for r in status_result.all()}

    # Rejected = assets that are draft AND have a rejection_comment
    rejected_result = await db.execute(
        select(func.count(MediaAsset.id)).where(
            MediaAsset.created_at >= since,
            MediaAsset.rejection_comment.isnot(None),
        )
    )
    total_rejected = rejected_result.scalar() or 0

    # AI usage
    ai_result = await db.execute(
        select(
            func.count(AIUsageLog.id),
            func.coalesce(func.sum(AIUsageLog.cost_millicents), 0),
        ).where(AIUsageLog.created_at >= since)
    )
    ai_row = ai_result.one()
    ai_actions = ai_row[0] or 0
    ai_cost_cents = float(ai_row[1] or 0) / 1000  # millicents → cents

    result = OverviewOut(
        total_assets=total_assets,
        total_approved=total_approved,
        total_rejected=total_rejected,
        avg_approval_time_hours=None,  # Would require tracking status change timestamps
        ai_actions_count=ai_actions,
        ai_cost_cents=round(ai_cost_cents, 2),
        compliance_avg_score=avg_compliance,
        assets_by_status=assets_by_status,
    )
    await cache_set(key, result.model_dump(), CACHE_TTL)
    return result


@router.get("/trends", response_model=list[TrendPoint])
async def get_trends(
    days: int = Query(90, ge=7, le=365),
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Time series data for trend charts (weekly buckets)."""
    key = _cache_key(current_user.tenant_id, "trends", days)
    cached = await cache_get(key)
    if cached:
        return [TrendPoint(**p) for p in cached]

    since = datetime.utcnow() - timedelta(days=days)

    # Weekly asset stats
    # Use date_trunc to group by week
    asset_result = await db.execute(
        select(
            func.date_trunc("week", MediaAsset.created_at).label("period"),
            func.count(MediaAsset.id).label("uploads"),
            func.count(case((MediaAsset.status == AssetStatus.approved, 1))).label("approvals"),
            func.avg(
                case(
                    (MediaAsset.compliance_score.isnot(None), cast(MediaAsset.compliance_score, Float)),
                )
            ).label("avg_compliance"),
        )
        .where(MediaAsset.created_at >= since)
        .group_by(text("1"))
        .order_by(text("1"))
    )
    asset_weeks = {row.period: row for row in asset_result.all()}

    # Weekly AI stats
    ai_result = await db.execute(
        select(
            func.date_trunc("week", AIUsageLog.created_at).label("period"),
            func.count(AIUsageLog.id).label("ai_actions"),
        )
        .where(AIUsageLog.created_at >= since)
        .group_by(text("1"))
        .order_by(text("1"))
    )
    ai_weeks = {row.period: row.ai_actions for row in ai_result.all()}

    # Combine
    all_periods = sorted(set(list(asset_weeks.keys()) + list(ai_weeks.keys())))
    points = []
    for period in all_periods:
        aw = asset_weeks.get(period)
        points.append(TrendPoint(
            period=period.strftime("%Y-W%V") if period else "",
            uploads=aw.uploads if aw else 0,
            approvals=aw.approvals if aw else 0,
            rejections=0,  # Would need rejection tracking
            ai_actions=ai_weeks.get(period, 0),
            avg_compliance=round(float(aw.avg_compliance), 1) if aw and aw.avg_compliance else None,
        ))

    await cache_set(key, [p.model_dump() for p in points], CACHE_TTL)
    return points


@router.get("/team", response_model=list[TeamMember])
async def get_team_stats(
    days: int = Query(30, ge=1, le=365),
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Per-team-member productivity stats."""
    key = _cache_key(current_user.tenant_id, "team", days)
    cached = await cache_get(key)
    if cached:
        return [TeamMember(**m) for m in cached]

    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            User.id,
            User.full_name,
            func.count(case((MediaAsset.created_at >= since, MediaAsset.id))).label("uploads"),
            func.count(
                case((
                    (MediaAsset.status == AssetStatus.approved) & (MediaAsset.created_at >= since),
                    MediaAsset.id,
                ))
            ).label("approvals"),
        )
        .outerjoin(MediaAsset, MediaAsset.uploaded_by == User.id)
        .group_by(User.id, User.full_name)
        .order_by(text("uploads DESC"))
    )

    members = [
        TeamMember(
            user_id=str(row.id),
            full_name=row.full_name,
            uploads=row.uploads,
            approvals=row.approvals,
        )
        for row in result.all()
    ]
    await cache_set(key, [m.model_dump() for m in members], CACHE_TTL)
    return members


@router.get("/ai", response_model=AIUsageDetail)
async def get_ai_usage(
    days: int = Query(30, ge=1, le=365),
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """AI usage breakdown by action type."""
    key = _cache_key(current_user.tenant_id, "ai", days)
    cached = await cache_get(key)
    if cached:
        return AIUsageDetail(**cached)

    since = datetime.utcnow() - timedelta(days=days)

    # By type
    type_result = await db.execute(
        select(AIUsageLog.action_type, func.count(AIUsageLog.id))
        .where(AIUsageLog.created_at >= since)
        .group_by(AIUsageLog.action_type)
    )
    actions_by_type = {row[0].value: row[1] for row in type_result.all()}

    # Totals
    cost_result = await db.execute(
        select(func.coalesce(func.sum(AIUsageLog.cost_millicents), 0))
        .where(AIUsageLog.created_at >= since)
    )
    total_millicents = cost_result.scalar() or 0
    total_cost_cents = float(total_millicents) / 1000

    # Unique assets with AI actions
    asset_count_result = await db.execute(
        select(func.count(func.distinct(AIUsageLog.asset_id)))
        .where(AIUsageLog.created_at >= since, AIUsageLog.asset_id.isnot(None))
    )
    unique_assets = asset_count_result.scalar() or 1  # avoid div by zero

    detail = AIUsageDetail(
        actions_by_type=actions_by_type,
        total_cost_cents=round(total_cost_cents, 2),
        avg_cost_per_asset_cents=round(total_cost_cents / unique_assets, 2),
    )
    await cache_set(key, detail.model_dump(), CACHE_TTL)
    return detail


@router.get("/roi", response_model=ROIOut)
async def get_roi(
    days: int = Query(30, ge=1, le=365),
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Estimated ROI — hours saved, cost saved based on industry benchmarks.

    Benchmarks:
    - Average marketing professional: $45/hour
    - Manual caption + hashtag + compliance: ~15 min per asset
    - Bluewave AI: ~30 seconds per asset
    """
    key = _cache_key(current_user.tenant_id, "roi", days)
    cached = await cache_get(key)
    if cached:
        return ROIOut(**cached)

    since = datetime.utcnow() - timedelta(days=days)

    # Count assets processed by AI
    ai_result = await db.execute(
        select(func.count(func.distinct(AIUsageLog.asset_id)))
        .where(AIUsageLog.created_at >= since, AIUsageLog.asset_id.isnot(None))
    )
    assets_processed = ai_result.scalar() or 0

    # Estimated time savings: 15 min manual vs 0.5 min AI = 14.5 min saved per asset
    hours_saved = round(assets_processed * 14.5 / 60, 1)
    cost_saved = round(hours_saved * 45, 2)  # $45/hour

    roi = ROIOut(
        estimated_hours_saved=hours_saved,
        estimated_cost_saved_usd=cost_saved,
        assets_processed=assets_processed,
        avg_time_to_approval_hours=None,
    )
    await cache_set(key, roi.model_dump(), CACHE_TTL)
    return roi


@router.get("/ai-quality", response_model=AIQualityMetrics)
async def get_ai_quality(
    days: int = Query(30, ge=1, le=365),
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """AI quality metrics — fallback rates, parse success, latency.

    Computed from local ai_usage_logs data. When LangSmith is configured,
    richer metrics (LLM evaluator scores) can be fetched from the LangSmith API.
    """
    key = _cache_key(current_user.tenant_id, "ai-quality", days)
    cached = await cache_get(key)
    if cached:
        return AIQualityMetrics(**cached)

    since = datetime.utcnow() - timedelta(days=days)

    from app.models.ai_usage import AIActionType

    async def _action_stats(action: AIActionType) -> dict:
        result = await db.execute(
            select(
                func.count(AIUsageLog.id).label("total"),
                func.avg(cast(AIUsageLog.input_tokens + AIUsageLog.output_tokens, Float)).label("avg_tokens"),
            ).where(
                AIUsageLog.created_at >= since,
                AIUsageLog.action_type == action,
            )
        )
        row = result.one()
        return {
            "total_actions": row.total or 0,
            "avg_tokens": round(float(row.avg_tokens or 0), 1),
        }

    caption_stats = await _action_stats(AIActionType.caption)
    hashtag_stats = await _action_stats(AIActionType.hashtags)
    compliance_stats = await _action_stats(AIActionType.compliance_check)

    # Compliance fallback rate: assets with score=50 vs total checked
    compliance_total = await db.execute(
        select(
            func.count(MediaAsset.id).label("total"),
            func.count(case((MediaAsset.compliance_score == 50, 1))).label("fallback"),
        ).where(
            MediaAsset.created_at >= since,
            MediaAsset.compliance_score.isnot(None),
        )
    )
    c_row = compliance_total.one()
    total_checked = c_row.total or 0
    compliance_fallback_count = c_row.fallback or 0

    metrics = AIQualityMetrics(
        caption_quality={
            **caption_stats,
            "note": "Detailed quality scores available via LangSmith dashboard",
        },
        hashtags_quality={
            **hashtag_stats,
            "note": "JSON parse success tracking available via LangSmith traces",
        },
        compliance_quality={
            **compliance_stats,
            "total_checked": total_checked,
            "fallback_rate": round(compliance_fallback_count / max(total_checked, 1) * 100, 1),
            "avg_score": None,  # Populated from LangSmith when available
        },
    )
    await cache_set(key, metrics.model_dump(), CACHE_TTL)
    return metrics


@router.get("/predictions")
async def get_predictions(
    current_user: UserContext = Depends(require_role("admin")),
):
    """AI-powered content predictions and recommendations."""
    from app.services.prediction_service import get_predictions as _get
    return await _get(current_user.tenant_id)


@router.get("/report")
async def get_monthly_report(
    year: int = Query(..., ge=2024, le=2030),
    month: int = Query(..., ge=1, le=12),
    current_user: UserContext = Depends(require_role("admin")),
):
    """Generate and download a monthly executive PDF report."""
    import os

    from app.services.report_service import generate_monthly_report

    file_path = await generate_monthly_report(current_user.tenant_id, year, month)
    if not os.path.exists(file_path):
        from fastapi import HTTPException
        raise HTTPException(500, "Report generation failed")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path),
    )
