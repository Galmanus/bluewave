"""Workflow Automation Engine.

Evaluates triggers, checks conditions, and executes actions autonomously.
Called from routers after state changes (upload, submit, approve, reject).

Action types:
  - auto_submit: move asset from draft → pending_approval
  - auto_approve: approve if compliance_score >= threshold
  - auto_reject: reject if compliance_score < threshold
  - run_compliance: trigger brand compliance check
  - notify_webhook: send event to all webhooks
  - add_to_collection: add approved asset to a portal collection
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.asset import AssetStatus, MediaAsset
from app.models.automation import Automation, AutomationLog, AutomationTrigger
from app.models.portal import PortalCollectionAsset
from app.services.webhook_service import emit_event

logger = logging.getLogger("bluewave.automations")


def _evaluate_conditions(conditions: list[dict], asset: MediaAsset) -> bool:
    """Check if all conditions are met for an asset."""
    for cond in conditions:
        field = cond.get("field", "")
        operator = cond.get("operator", "eq")
        value = cond.get("value")

        actual = getattr(asset, field, None)
        if actual is None:
            return False

        # Convert for comparison
        if isinstance(actual, int) or isinstance(actual, float):
            try:
                value = type(actual)(value)
            except (ValueError, TypeError):
                return False

        if operator == "eq" and actual != value:
            return False
        elif operator == "neq" and actual == value:
            return False
        elif operator == "gt" and not (actual > value):
            return False
        elif operator == "lt" and not (actual < value):
            return False
        elif operator == "gte" and not (actual >= value):
            return False
        elif operator == "lte" and not (actual <= value):
            return False
        elif operator == "starts_with" and not str(actual).startswith(str(value)):
            return False
        elif operator == "contains" and str(value) not in str(actual):
            return False

    return True


async def _execute_action(
    action: dict,
    asset: MediaAsset,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Execute a single automation action. Returns result dict."""
    action_type = action.get("type", "")
    config = action.get("config", {})
    result = {"type": action_type, "status": "success"}

    try:
        if action_type == "auto_submit":
            if asset.status == AssetStatus.draft:
                asset.status = AssetStatus.pending_approval
                asset.rejection_comment = None
                result["detail"] = "Asset auto-submitted for approval"
            else:
                result["status"] = "skipped"
                result["detail"] = f"Asset status is {asset.status.value}, not draft"

        elif action_type == "auto_approve":
            min_score = config.get("min_compliance_score", 90)
            if asset.status == AssetStatus.pending_approval:
                if asset.compliance_score is not None and asset.compliance_score >= min_score:
                    asset.status = AssetStatus.approved
                    result["detail"] = f"Auto-approved (compliance {asset.compliance_score} >= {min_score})"
                else:
                    result["status"] = "skipped"
                    score = asset.compliance_score or "not checked"
                    result["detail"] = f"Compliance score {score} below threshold {min_score}"
            else:
                result["status"] = "skipped"
                result["detail"] = f"Asset status is {asset.status.value}, not pending_approval"

        elif action_type == "auto_reject":
            max_score = config.get("max_compliance_score", 50)
            if asset.status == AssetStatus.pending_approval:
                if asset.compliance_score is not None and asset.compliance_score < max_score:
                    asset.status = AssetStatus.draft
                    asset.rejection_comment = f"Auto-rejected: compliance score {asset.compliance_score} below {max_score}"
                    result["detail"] = asset.rejection_comment
                else:
                    result["status"] = "skipped"
            else:
                result["status"] = "skipped"

        elif action_type == "run_compliance":
            # Trigger compliance check (import here to avoid circular)
            from app.models.brand_guideline import BrandGuideline
            from app.services.compliance_service import check_compliance

            g_result = await db.execute(
                select(BrandGuideline).where(
                    BrandGuideline.tenant_id == tenant_id,
                    BrandGuideline.is_active.is_(True),
                )
            )
            guidelines = g_result.scalar_one_or_none()
            if guidelines:
                compliance = await check_compliance(
                    file_path=asset.file_path,
                    file_type=asset.file_type,
                    caption=asset.caption,
                    hashtags=asset.hashtags,
                    guidelines=guidelines,
                )
                asset.compliance_score = compliance.score
                asset.compliance_issues = [
                    {"severity": i.severity, "category": i.category,
                     "message": i.message, "suggestion": i.suggestion}
                    for i in compliance.issues
                ]
                result["detail"] = f"Compliance checked: score {compliance.score}"
            else:
                result["status"] = "skipped"
                result["detail"] = "No brand guidelines configured"

        elif action_type == "notify_webhook":
            await emit_event(
                tenant_id,
                f"automation.{action_type}",
                {"asset_id": str(asset.id), "automation_action": action_type},
            )
            result["detail"] = "Webhook notification sent"

        elif action_type == "add_to_collection":
            collection_id = config.get("collection_id")
            if collection_id and asset.status == AssetStatus.approved:
                link = PortalCollectionAsset(
                    collection_id=uuid.UUID(collection_id),
                    asset_id=asset.id,
                )
                db.add(link)
                result["detail"] = f"Added to collection {collection_id}"
            else:
                result["status"] = "skipped"

        else:
            result["status"] = "unknown"
            result["detail"] = f"Unknown action type: {action_type}"

    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
        logger.exception("Action %s failed for asset %s", action_type, asset.id)

    return result


async def on_event(
    event_type: str,
    asset_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    """Main entry point: called from routers after state changes.

    Finds matching automations for this event and executes them.
    """
    # Map event names to trigger enum
    trigger_map = {
        "asset_uploaded": AutomationTrigger.asset_uploaded,
        "asset_submitted": AutomationTrigger.asset_submitted,
        "asset_approved": AutomationTrigger.asset_approved,
        "asset_rejected": AutomationTrigger.asset_rejected,
        "compliance_checked": AutomationTrigger.compliance_checked,
    }
    trigger = trigger_map.get(event_type)
    if not trigger:
        return

    async with async_session_factory() as db:
        # Get matching automations
        auto_result = await db.execute(
            select(Automation).where(
                Automation.tenant_id == tenant_id,
                Automation.trigger_type == trigger,
                Automation.is_active.is_(True),
            )
        )
        automations = auto_result.scalars().all()
        if not automations:
            return

        # Get asset
        asset_result = await db.execute(
            select(MediaAsset).where(MediaAsset.id == asset_id)
        )
        asset = asset_result.scalar_one_or_none()
        if not asset:
            return

        for auto in automations:
            # Check conditions
            conditions = auto.conditions if isinstance(auto.conditions, list) else []
            if conditions and not _evaluate_conditions(conditions, asset):
                logger.debug("Automation %s: conditions not met for asset %s", auto.name, asset_id)
                continue

            # Execute actions
            actions = auto.actions if isinstance(auto.actions, list) else []
            action_results = []
            for action in actions:
                res = await _execute_action(action, asset, tenant_id, db)
                action_results.append(res)

            # Log execution
            status = "success"
            if any(r["status"] == "error" for r in action_results):
                status = "partial"

            log = AutomationLog(
                tenant_id=tenant_id,
                automation_id=auto.id,
                asset_id=asset_id,
                trigger_type=event_type,
                actions_executed=action_results,
                status=status,
            )
            db.add(log)

            # Update automation stats
            auto.run_count += 1
            auto.last_run_at = datetime.now(timezone.utc)

            logger.info(
                "Automation '%s' executed: %d actions, status=%s",
                auto.name, len(action_results), status,
            )

        await db.commit()
