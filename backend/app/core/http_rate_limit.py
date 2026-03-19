"""In-memory HTTP rate limiter middleware.

Limits requests per IP per route pattern. Returns 429 when exceeded.
Phase 1: dict-based. Phase 2: migrate to Redis.
"""

import logging
import time
import threading
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("bluewave.rate_limit")

# Route pattern → (max_requests, window_seconds)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth/": (10, 60),       # 10 req/min for auth
    "/api/v1/ai/": (60, 60),         # 60 req/min for AI
    "/api/v1/assets": (30, 60),      # 30 req/min for upload-heavy
    "default": (120, 60),            # 120 req/min general
}

# In-memory store: {ip:route_key: [(timestamp, ...)] }
_buckets: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()

# Cleanup old entries every N requests
_CLEANUP_INTERVAL = 500
_request_counter = 0


def _cleanup() -> None:
    """Remove expired entries from all buckets."""
    now = time.time()
    cutoff = now - 120  # keep 2 min of history
    with _lock:
        expired_keys = []
        for key, timestamps in _buckets.items():
            _buckets[key] = [t for t in timestamps if t > cutoff]
            if not _buckets[key]:
                expired_keys.append(key)
        for key in expired_keys:
            del _buckets[key]


def _get_limit_for_path(path: str) -> tuple[int, int]:
    """Find the matching rate limit for a request path."""
    for prefix, limit in RATE_LIMITS.items():
        if prefix != "default" and path.startswith(prefix):
            return limit
    return RATE_LIMITS["default"]


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        global _request_counter

        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # Skip health checks
        if path.startswith("/api/v1/health"):
            return await call_next(request)

        max_requests, window = _get_limit_for_path(path)
        # Use route prefix as bucket key (not full path)
        route_key = path.rsplit("/", 1)[0] if "/" in path[1:] else path
        bucket_key = f"{client_ip}:{route_key}"

        now = time.time()
        cutoff = now - window

        with _lock:
            timestamps = _buckets[bucket_key]
            # Remove expired
            timestamps[:] = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= max_requests:
                retry_after = int(window - (now - timestamps[0])) + 1
                logger.warning(
                    "Rate limit exceeded: ip=%s path=%s count=%d limit=%d",
                    client_ip, path, len(timestamps), max_requests,
                )
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)

        # Periodic cleanup
        _request_counter += 1
        if _request_counter % _CLEANUP_INTERVAL == 0:
            _cleanup()

        return await call_next(request)
