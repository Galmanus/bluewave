import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from app.core.deps import UserContext, get_current_user, require_role
from app.core.tenant import get_tenant_db
from app.models.asset import AssetStatus, MediaAsset
from app.models.brand_guideline import BrandGuideline
from app.models.user import User
from app.schemas.asset import AssetOut, RejectRequest
from app.services.automation_engine import on_event as run_automations
from app.services.compliance_service import check_compliance
from app.services.email_service import send_asset_notification
from app.services.webhook_service import emit_event
from app.core.tracing import send_feedback as send_langsmith_feedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["workflow"])


async def _run_compliance_on_submit(
    asset_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Background: run brand compliance check after asset submission.

    If guidelines exist, check compliance and store score on asset.
    This runs asynchronously — doesn't block the submit response.
    """
    from app.core.database import async_session_factory
    from app.models.ai_usage import AIActionType
    from app.services.ai_usage import log_ai_usage

    try:
        async with async_session_factory() as db:
            # Get guidelines (bypass tenant filter — direct query)
            g_result = await db.execute(
                select(BrandGuideline).where(
                    BrandGuideline.tenant_id == tenant_id,
                    BrandGuideline.is_active.is_(True),
                )
            )
            guidelines = g_result.scalar_one_or_none()
            if not guidelines:
                return  # No guidelines → skip

            # Get asset
            a_result = await db.execute(
                select(MediaAsset).where(MediaAsset.id == asset_id)
            )
            asset = a_result.scalar_one_or_none()
            if not asset:
                return

            # Run compliance
            result = await check_compliance(
                file_path=asset.file_path,
                file_type=asset.file_type,
                caption=asset.caption,
                hashtags=asset.hashtags,
                guidelines=guidelines,
            )

            # Store on asset
            asset.compliance_score = result.score
            asset.compliance_issues = [
                {"severity": i.severity, "category": i.category,
                 "message": i.message, "suggestion": i.suggestion}
                for i in result.issues
            ]

            # Log usage
            await log_ai_usage(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                asset_id=asset_id,
                action_type=AIActionType.compliance_check,
            )

            await db.commit()
            logger.info(
                "Auto-compliance for asset %s: score=%d, passed=%s",
                asset_id, result.score, result.passed,
            )

    except Exception:
        logger.exception("Auto-compliance check failed for asset %s", asset_id)


async def _send_approval_feedback(asset_id: uuid.UUID, tenant_id: uuid.UUID, approved: bool, comment: str = "") -> None:
    """Send user approval/rejection feedback to LangSmith (fire-and-forget)."""
    try:
        from app.core.database import async_session_factory
        from app.models.ai_usage import AIActionType, AIUsageLog

        async with async_session_factory() as db:
            result = await db.execute(
                select(AIUsageLog.langsmith_run_id)
                .where(
                    AIUsageLog.asset_id == asset_id,
                    AIUsageLog.action_type == AIActionType.caption,
                    AIUsageLog.langsmith_run_id.isnot(None),
                )
                .order_by(AIUsageLog.created_at.desc())
                .limit(1)
            )
            run_id = result.scalar_one_or_none()
            if run_id:
                send_langsmith_feedback(
                    run_id=run_id,
                    key="user_approval",
                    score=1.0 if approved else 0.0,
                    comment=comment or ("approved" if approved else "rejected"),
                )
                logger.debug("Sent LangSmith feedback for asset %s, run %s", asset_id, run_id)
    except Exception:
        logger.debug("Failed to send LangSmith approval feedback for asset %s", asset_id)


def _asset_summary(asset: MediaAsset) -> dict:
    return {
        "asset_id": str(asset.id),
        "file_type": asset.file_type,
        "caption": asset.caption,
        "status": asset.status.value,
    }


@router.post("/{asset_id}/submit", response_model=AssetOut)
async def submit_for_approval(
    asset_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.uploaded_by != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the asset owner or admin can submit")

    if asset.status != AssetStatus.draft:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit: asset is '{asset.status.value}', must be 'draft'",
        )

    asset.status = AssetStatus.pending_approval
    asset.rejection_comment = None
    await db.commit()
    await db.refresh(asset)

    background_tasks.add_task(
        emit_event, current_user.tenant_id, "asset.submitted", _asset_summary(asset)
    )
    background_tasks.add_task(
        run_automations, "asset_submitted", asset.id, current_user.tenant_id
    )

    # Auto-compliance check if brand guidelines exist
    background_tasks.add_task(
        _run_compliance_on_submit,
        asset.id,
        current_user.tenant_id,
        current_user.user_id,
    )

    return asset


@router.post("/{asset_id}/approve", response_model=AssetOut)
async def approve_asset(
    asset_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.status != AssetStatus.pending_approval:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve: asset is '{asset.status.value}', must be 'pending_approval'",
        )

    # Compliance gate: block approval if score is below threshold
    if asset.compliance_score is not None and asset.compliance_score < 70:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve: compliance score is {asset.compliance_score}/100 (minimum 70 required). Fix the compliance issues first.",
        )

    asset.status = AssetStatus.approved
    await db.commit()
    await db.refresh(asset)

    background_tasks.add_task(
        emit_event, current_user.tenant_id, "asset.approved", _asset_summary(asset)
    )
    background_tasks.add_task(
        run_automations, "asset_approved", asset.id, current_user.tenant_id
    )
    background_tasks.add_task(
        _send_approval_feedback, asset.id, current_user.tenant_id, True
    )

    # Notify the uploader via email
    uploader_result = await db.execute(
        select(User).where(User.id == asset.uploaded_by)
    )
    uploader = uploader_result.scalar_one_or_none()
    if uploader:
        approver_result = await db.execute(
            select(User.full_name).where(User.id == current_user.user_id)
        )
        approver_name = approver_result.scalar_one_or_none() or "An admin"
        background_tasks.add_task(
            send_asset_notification,
            uploader.email,
            "approved",
            asset.caption or "",
            approver_name,
            str(asset.id),
        )

    return asset


@router.post("/{asset_id}/reject", response_model=AssetOut)
async def reject_asset(
    asset_id: uuid.UUID,
    body: RejectRequest,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.status != AssetStatus.pending_approval:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject: asset is '{asset.status.value}', must be 'pending_approval'",
        )

    asset.status = AssetStatus.draft
    asset.rejection_comment = body.comment
    await db.commit()
    await db.refresh(asset)

    background_tasks.add_task(
        emit_event,
        current_user.tenant_id,
        "asset.rejected",
        {**_asset_summary(asset), "rejection_comment": body.comment},
    )
    background_tasks.add_task(
        run_automations, "asset_rejected", asset.id, current_user.tenant_id
    )
    background_tasks.add_task(
        _send_approval_feedback, asset.id, current_user.tenant_id, False, body.comment
    )

    # Notify the uploader via email
    uploader_result = await db.execute(
        select(User).where(User.id == asset.uploaded_by)
    )
    uploader = uploader_result.scalar_one_or_none()
    if uploader:
        rejector_result = await db.execute(
            select(User.full_name).where(User.id == current_user.user_id)
        )
        rejector_name = rejector_result.scalar_one_or_none() or "An admin"
        background_tasks.add_task(
            send_asset_notification,
            uploader.email,
            "rejected",
            asset.caption or "",
            rejector_name,
            str(asset.id),
        )

    return asset
