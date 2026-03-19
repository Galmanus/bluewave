"""Audit logging service — records critical actions for compliance."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger("bluewave.audit")


async def log_action(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Record an auditable action.

    Actions: login, logout, asset.create, asset.delete, asset.approve,
    asset.reject, user.invite, user.remove, settings.change,
    api_key.create, api_key.revoke, webhook.create, webhook.delete
    """
    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)

    logger.info(
        "Audit: %s by user %s on %s/%s",
        action, user_id, resource_type, resource_id,
    )
    return entry
