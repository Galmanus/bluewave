"""Webhook delivery service.

Dispatches events to registered webhook URLs with HMAC signing,
retry logic, and async HTTP delivery via httpx.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.retry import retry
from app.models.webhook import Webhook

logger = logging.getLogger("bluewave.webhooks")

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Create HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()


@retry(max_retries=3, base_delay=2.0, retryable=(httpx.TransportError, httpx.HTTPStatusError))
async def _deliver(url: str, payload: dict, secret: str | None) -> None:
    """Deliver a single webhook with retry."""
    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Bluewave-Webhooks/1.0",
        "X-Bluewave-Event": payload.get("event", "unknown"),
        "X-Bluewave-Delivery": str(uuid.uuid4()),
    }
    if secret:
        sig = _sign_payload(body, secret)
        headers["X-Bluewave-Signature"] = f"sha256={sig}"
        headers["X-Webhook-Signature"] = sig  # OpenClaw compatibility

    import time
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(url, content=body, headers=headers)
        resp.raise_for_status()

    duration_ms = round((time.perf_counter() - t0) * 1000, 1)
    logger.info(
        "Webhook delivered",
        extra={
            "event": payload.get("event"), "url": url,
            "status_code": resp.status_code, "duration_ms": duration_ms,
        },
    )


async def emit_event(
    tenant_id: uuid.UUID,
    event: str,
    data: dict,
) -> None:
    """Emit an event to all matching webhooks for a tenant.

    Called from routers after state changes. Runs in background — never
    blocks the API response.
    """
    async with async_session_factory() as db:
        result = await db.execute(
            select(Webhook).where(
                Webhook.tenant_id == tenant_id,
                Webhook.is_active.is_(True),
            )
        )
        webhooks = result.scalars().all()

    payload = {
        "event": event,
        "tenant_id": str(tenant_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }

    for wh in webhooks:
        # Check if webhook is subscribed to this event
        subscribed = wh.events.strip()
        if subscribed != "*" and event not in subscribed.split(","):
            continue
        try:
            await _deliver(wh.url, payload, wh.secret)
        except Exception:
            logger.exception("Webhook delivery failed: %s → %s", event, wh.url)
