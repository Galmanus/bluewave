import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.http_rate_limit import RateLimitMiddleware
from app.core.logging_config import setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.routers import (
    ai,
    analytics,
    api_keys,
    assets,
    audit,
    auth,
    automations,
    brand,
    briefs,
    calendar,
    comments,
    health,
    permissions,
    resize,
    portals,
    sso,
    subscriptions,
    trends,
    users,
    versions,
    webhooks,
    workflow,
)

setup_logging()
logger = logging.getLogger("bluewave.startup")

app = FastAPI(title="Bluewave API", version="0.4.0")

# Middleware stack (added in reverse order — first added = outermost)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")
app.include_router(workflow.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(trends.router, prefix="/api/v1")
app.include_router(brand.router, prefix="/api/v1")
app.include_router(portals.router, prefix="/api/v1")
app.include_router(automations.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(calendar.router, prefix="/api/v1")
app.include_router(comments.router, prefix="/api/v1")
app.include_router(briefs.router, prefix="/api/v1")
app.include_router(versions.router, prefix="/api/v1")
app.include_router(resize.router, prefix="/api/v1")
app.include_router(sso.router, prefix="/api/v1")
app.include_router(permissions.router, prefix="/api/v1")

from app.routers import wave_proxy
app.include_router(wave_proxy.router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup() -> None:
    settings.validate_production_settings()

    from app.core.sentry import init_sentry
    init_sentry()

    from app.core.tracing import init_tracing
    init_tracing()

    from app.services.scheduler import start_scheduler
    start_scheduler()

    logger.info(
        "Bluewave API starting",
        extra={
            "env": settings.ENV,
            "cors_origins": settings.cors_origins,
            "ai_model": settings.AI_MODEL,
        },
    )
