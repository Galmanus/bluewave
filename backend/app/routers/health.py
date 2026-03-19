"""Health check endpoints for monitoring and k8s probes."""

import os
import shutil
import time

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Comprehensive health check with component status."""
    checks: dict[str, dict] = {}
    overall = "ok"

    # Database check
    try:
        t0 = time.perf_counter()
        await db.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - t0) * 1000, 1)
        checks["database"] = {"status": "ok", "latency_ms": latency}
    except Exception as exc:
        checks["database"] = {"status": "error", "error": str(exc)}
        overall = "error"

    # AI service check
    ai_configured = bool(settings.ANTHROPIC_API_KEY)
    checks["ai_service"] = {
        "status": "ok" if ai_configured else "degraded",
        "type": "claude" if ai_configured else "stub",
        "api_key_configured": ai_configured,
    }
    if not ai_configured and overall == "ok":
        overall = "degraded"

    # Storage check
    uploads_dir = "/app/uploads"
    uploads_exists = os.path.isdir(uploads_dir)
    free_space_mb = 0
    if uploads_exists:
        stat = shutil.disk_usage(uploads_dir)
        free_space_mb = round(stat.free / (1024 * 1024))
    checks["storage"] = {
        "status": "ok" if uploads_exists and free_space_mb > 100 else "degraded",
        "uploads_dir_exists": uploads_exists,
        "free_space_mb": free_space_mb,
    }

    return {
        "status": overall,
        "version": "0.3.0",
        "env": settings.ENV,
        "uptime_seconds": round(time.time() - _start_time),
        "checks": checks,
    }


@router.get("/health/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)) -> dict:
    """K8s readiness probe — only checks database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "not_ready"})


@router.get("/health/live")
async def liveness_probe() -> dict:
    """K8s liveness probe — always returns 200."""
    return {"status": "alive"}
