"""Request logging middleware with request_id tracking."""

import time
import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Context var for request_id — accessible from anywhere via structlog contextvars
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = structlog.get_logger("bluewave.http")

# Paths to skip logging (health checks, etc.)
SKIP_LOG_PATHS = {"/api/v1/health", "/api/v1/health/live", "/api/v1/health/ready"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = str(uuid.uuid4())
        request_id_var.set(rid)

        # Bind request_id to structlog context for all downstream logs
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid)

        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else "unknown"

        skip = path in SKIP_LOG_PATHS

        if not skip:
            logger.info(
                "request_started",
                method=method,
                path=path,
                client_ip=client_ip,
                user_agent=request.headers.get("user-agent", ""),
            )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            logger.exception(
                "request_failed",
                method=method,
                path=path,
                duration_ms=duration_ms,
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        # Add request ID header to response
        response.headers["X-Request-ID"] = rid

        if not skip:
            logger.info(
                "request_completed",
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        return response
