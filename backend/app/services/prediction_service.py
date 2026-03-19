"""Predictive analytics — identify content patterns and generate recommendations.

Uses historical data + Claude AI to predict what content types perform best.
Results are cached daily in Redis.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, cast, Float, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger("bluewave.predictions")


async def analyze_patterns(tenant_id: uuid.UUID, days: int = 90) -> dict:
    """Aggregate content metrics and generate AI-powered predictions."""
    from app.core.database import async_session_factory
    from app.models.ai_usage import AIUsageLog
    from app.models.asset import AssetStatus, MediaAsset

    since = datetime.now(timezone.utc) - timedelta(days=days)

    async with async_session_factory() as db:
        # Approval rate by day of week
        dow_result = await db.execute(
            select(
                func.extract("dow", MediaAsset.created_at).label("dow"),
                func.count(MediaAsset.id).label("total"),
                func.count(case((MediaAsset.status == AssetStatus.approved, 1))).label("approved"),
            )
            .where(MediaAsset.tenant_id == tenant_id, MediaAsset.created_at >= since)
            .group_by(func.extract("dow", MediaAsset.created_at))
        )
        by_dow = [{"day": int(r.dow), "total": r.total, "approved": r.approved} for r in dow_result.all()]

        # Compliance score distribution
        comp_result = await db.execute(
            select(
                func.avg(cast(MediaAsset.compliance_score, Float)).label("avg_score"),
                func.count(MediaAsset.id).label("total"),
            )
            .where(
                MediaAsset.tenant_id == tenant_id,
                MediaAsset.created_at >= since,
                MediaAsset.compliance_score.isnot(None),
            )
        )
        comp_row = comp_result.one()

        # Top hashtags
        # Note: array_unnest not available in all setups; aggregate from Python
        hashtag_result = await db.execute(
            select(MediaAsset.hashtags)
            .where(
                MediaAsset.tenant_id == tenant_id,
                MediaAsset.created_at >= since,
                MediaAsset.hashtags.isnot(None),
            )
        )
        tag_counts: dict[str, int] = {}
        for row in hashtag_result.all():
            if row[0]:
                for tag in row[0]:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Total assets and AI actions
        total_result = await db.execute(
            select(func.count(MediaAsset.id))
            .where(MediaAsset.tenant_id == tenant_id, MediaAsset.created_at >= since)
        )
        total_assets = total_result.scalar() or 0

    metrics = {
        "period_days": days,
        "total_assets": total_assets,
        "by_day_of_week": by_dow,
        "avg_compliance_score": round(float(comp_row.avg_score), 1) if comp_row.avg_score else None,
        "top_hashtags": [{"tag": t, "count": c} for t, c in top_tags],
    }

    # Generate AI recommendations if Claude is available
    recommendations = []
    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            resp = await client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Given these content operations metrics for the last {days} days:\n"
                        f"{json.dumps(metrics, indent=2)}\n\n"
                        "Identify the top 5 actionable patterns and predict what content types "
                        "will perform best. Return JSON array: "
                        '[{"pattern": "...", "insight": "...", "action": "...", "impact": "high|medium|low"}]'
                    ),
                }],
                system="You are a data-driven content strategist. Analyze metrics and provide actionable insights. Return ONLY valid JSON.",
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            recommendations = json.loads(raw)
        except Exception:
            logger.exception("AI prediction generation failed")

    return {
        "metrics": metrics,
        "recommendations": recommendations,
    }


async def get_predictions(tenant_id: uuid.UUID) -> dict:
    """Get cached predictions or generate fresh ones."""
    from app.core.cache import cache_get, cache_set

    cache_key = f"predictions:{tenant_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await analyze_patterns(tenant_id)
    await cache_set(cache_key, result, ttl=86400)  # Cache for 24 hours
    return result
