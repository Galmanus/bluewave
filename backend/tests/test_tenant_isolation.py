"""CRITICAL: Verify tenant A never sees tenant B's data.

Tenant isolation is enforced by the get_tenant_db dependency which filters
queries by the JWT's tenant_id. These tests ensure data created by one
tenant is completely invisible to another.
"""

import pytest



async def test_tenant_b_cannot_see_tenant_a_assets(
    client, admin_headers, admin_b_headers, draft_asset
):
    """Asset created in tenant A must not appear in tenant B's asset list."""
    # Tenant A sees the asset
    resp_a = await client.get("/api/v1/assets", headers=admin_headers)
    assert resp_a.status_code == 200
    ids_a = [item["id"] for item in resp_a.json()["items"]]
    assert str(draft_asset.id) in ids_a

    # Tenant B sees nothing
    resp_b = await client.get("/api/v1/assets", headers=admin_b_headers)
    assert resp_b.status_code == 200
    ids_b = [item["id"] for item in resp_b.json()["items"]]
    assert str(draft_asset.id) not in ids_b


async def test_tenant_b_cannot_see_tenant_a_webhooks(
    client, admin_headers, admin_b_headers, webhook
):
    """Webhook created in tenant A must not appear in tenant B's webhook list."""
    # Tenant A sees the webhook
    resp_a = await client.get("/api/v1/webhooks", headers=admin_headers)
    assert resp_a.status_code == 200
    ids_a = [item["id"] for item in resp_a.json()]
    assert str(webhook.id) in ids_a

    # Tenant B sees nothing
    resp_b = await client.get("/api/v1/webhooks", headers=admin_b_headers)
    assert resp_b.status_code == 200
    ids_b = [item["id"] for item in resp_b.json()]
    assert str(webhook.id) not in ids_b


async def test_tenant_b_asset_counts_are_zero(
    client, admin_headers, admin_b_headers, draft_asset
):
    """Tenant B's asset counts should be zero even though tenant A has assets."""
    # Tenant A has at least one asset
    resp_a = await client.get("/api/v1/assets/counts", headers=admin_headers)
    assert resp_a.status_code == 200
    assert resp_a.json()["total"] > 0

    # Tenant B has zero
    resp_b = await client.get("/api/v1/assets/counts", headers=admin_b_headers)
    assert resp_b.status_code == 200
    assert resp_b.json()["total"] == 0
    assert resp_b.json()["draft"] == 0
