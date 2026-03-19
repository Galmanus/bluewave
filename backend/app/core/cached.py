"""Cache helpers for common query patterns.

Usage in routers:
    from app.core.cached import cached_guidelines, invalidate_guidelines

    @router.get("/guidelines")
    async def get_guidelines(...):
        cached = await cached_guidelines(tenant_id)
        if cached is not None:
            return cached
        # ... normal DB query ...
"""

import uuid
from typing import Any

from app.core.cache import cache_delete, cache_get, cache_set


def _key(prefix: str, tenant_id: uuid.UUID) -> str:
    return f"tenant:{tenant_id}:{prefix}"


# -- Brand Guidelines (TTL 5 min) ------------------------------------------

async def cached_guidelines(tenant_id: uuid.UUID) -> Any | None:
    return await cache_get(_key("brand_guidelines", tenant_id))


async def set_guidelines_cache(tenant_id: uuid.UUID, data: Any) -> None:
    await cache_set(_key("brand_guidelines", tenant_id), data, ttl_seconds=300)


async def invalidate_guidelines(tenant_id: uuid.UUID) -> None:
    await cache_delete(_key("brand_guidelines", tenant_id))


# -- Billing Plan (TTL 1 min) ----------------------------------------------

async def cached_billing_plan(tenant_id: uuid.UUID) -> Any | None:
    return await cache_get(_key("billing_plan", tenant_id))


async def set_billing_plan_cache(tenant_id: uuid.UUID, data: Any) -> None:
    await cache_set(_key("billing_plan", tenant_id), data, ttl_seconds=60)


async def invalidate_billing_plan(tenant_id: uuid.UUID) -> None:
    await cache_delete(_key("billing_plan", tenant_id))


# -- Asset Counts (TTL 30 sec) ---------------------------------------------

async def cached_asset_counts(tenant_id: uuid.UUID) -> Any | None:
    return await cache_get(_key("asset_counts", tenant_id))


async def set_asset_counts_cache(tenant_id: uuid.UUID, data: Any) -> None:
    await cache_set(_key("asset_counts", tenant_id), data, ttl_seconds=30)


async def invalidate_asset_counts(tenant_id: uuid.UUID) -> None:
    await cache_delete(_key("asset_counts", tenant_id))
