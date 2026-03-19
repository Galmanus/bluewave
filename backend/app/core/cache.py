"""Redis cache layer with graceful fallback when unavailable."""

import json
import logging
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger("bluewave.cache")

_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Get or create the Redis connection pool. Returns None if unavailable."""
    global _pool
    if _pool is not None:
        return _pool
    if not settings.REDIS_URL:
        return None
    try:
        _pool = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await _pool.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
        return _pool
    except Exception:
        logger.warning("Redis unavailable — caching disabled")
        _pool = None
        return None


async def cache_get(key: str) -> Any | None:
    """Get a cached value. Returns None on miss or if Redis unavailable."""
    r = await get_redis()
    if not r:
        return None
    try:
        val = await r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """Set a cached value with TTL."""
    r = await get_redis()
    if not r:
        return
    try:
        await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    """Delete a cached key."""
    r = await get_redis()
    if not r:
        return
    try:
        await r.delete(key)
    except Exception:
        pass


async def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern (e.g., 'tenant:xxx:*')."""
    r = await get_redis()
    if not r:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass
