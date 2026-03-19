import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, get_current_user, require_role
from app.core.tenant import get_tenant_db
from app.models.asset import MediaAsset
from app.models.brand_guideline import BrandGuideline
from app.schemas.brand import (
    BrandGuidelineCreate,
    BrandGuidelineOut,
    ComplianceIssueOut,
    ComplianceResultOut,
)
from app.services.compliance_service import check_compliance
from app.services.webhook_service import emit_event

router = APIRouter(prefix="/brand", tags=["brand"])


async def _get_active_guideline(
    db: AsyncSession,
) -> BrandGuideline | None:
    result = await db.execute(
        select(BrandGuideline).where(BrandGuideline.is_active.is_(True)).limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/guidelines", response_model=BrandGuidelineOut | None)
async def get_guidelines(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Get the active brand guidelines for this tenant."""
    return await _get_active_guideline(db)


@router.put("/guidelines", response_model=BrandGuidelineOut)
async def upsert_guidelines(
    body: BrandGuidelineCreate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Create or update brand guidelines. Only one active guideline per tenant."""
    existing = await _get_active_guideline(db)

    if existing:
        # Update existing
        if body.primary_colors is not None:
            existing.primary_colors = body.primary_colors
        if body.secondary_colors is not None:
            existing.secondary_colors = body.secondary_colors
        if body.fonts is not None:
            existing.fonts = body.fonts
        if body.tone_description is not None:
            existing.tone_description = body.tone_description
        if body.dos is not None:
            existing.dos = body.dos
        if body.donts is not None:
            existing.donts = body.donts
        if body.custom_rules is not None:
            existing.custom_rules = body.custom_rules
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        # Create new
        guideline = BrandGuideline(
            tenant_id=current_user.tenant_id,
            primary_colors=body.primary_colors,
            secondary_colors=body.secondary_colors,
            fonts=body.fonts,
            tone_description=body.tone_description,
            dos=body.dos,
            donts=body.donts,
            custom_rules=body.custom_rules,
            is_active=True,
        )
        db.add(guideline)
        await db.commit()
        await db.refresh(guideline)
        return guideline


@router.post("/check/{asset_id}", response_model=ComplianceResultOut)
async def check_asset_compliance(
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Run brand compliance check on an asset using Claude AI."""
    from app.core.rate_limit import check_ai_rate_limit
    await check_ai_rate_limit(db, current_user.tenant_id)

    # Get asset
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Get guidelines
    guidelines = await _get_active_guideline(db)
    if not guidelines:
        raise HTTPException(
            status_code=400,
            detail="No brand guidelines configured. Set up guidelines first.",
        )

    # Run compliance check
    compliance = await check_compliance(
        file_path=asset.file_path,
        file_type=asset.file_type,
        caption=asset.caption,
        hashtags=asset.hashtags,
        guidelines=guidelines,
    )

    # Store result on the asset
    asset.compliance_score = compliance.score
    asset.compliance_issues = [
        {
            "severity": i.severity,
            "category": i.category,
            "message": i.message,
            "suggestion": i.suggestion,
        }
        for i in compliance.issues
    ]
    await db.commit()

    # Log AI usage
    from app.models.ai_usage import AIActionType
    from app.services.ai_usage import log_ai_usage

    await log_ai_usage(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
        asset_id=asset.id,
        action_type=AIActionType.compliance_check,
    )
    await db.commit()

    return ComplianceResultOut(
        score=compliance.score,
        passed=compliance.passed,
        summary=compliance.summary,
        issues=[
            ComplianceIssueOut(
                severity=i.severity,
                category=i.category,
                message=i.message,
                suggestion=i.suggestion,
            )
            for i in compliance.issues
        ],
    )
