"""Sentry error tracking integration.

Initializes Sentry SDK if SENTRY_DSN is configured.
Skips silently otherwise (development/testing).
"""

import logging

from app.core.config import settings

logger = logging.getLogger("bluewave.sentry")


def init_sentry() -> bool:
    """Initialize Sentry SDK. Returns True if configured."""
    if not settings.SENTRY_DSN:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENV,
            traces_sample_rate=0.1,
            send_default_pii=False,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
        )
        logger.info("Sentry initialized (env=%s)", settings.ENV)
        return True
    except Exception:
        logger.warning("Failed to initialize Sentry")
        return False


def set_sentry_user(user_id: str, tenant_id: str) -> None:
    """Set user context on the current Sentry scope (IDs only, no PII)."""
    try:
        import sentry_sdk
        sentry_sdk.set_user({"id": user_id})
        sentry_sdk.set_tag("tenant_id", tenant_id)
    except Exception:
        pass
