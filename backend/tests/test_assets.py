"""Tests for the assets router — CRUD endpoints."""

from __future__ import annotations

import uuid

import pytest

from app.models.asset import MediaAsset


BASE = "/api/v1/assets"


# ---- 1. GET /assets/counts ------------------------------------------------

async def test_counts_returns_status_breakdown(
    client, admin_headers, draft_asset, pending_asset, approved_asset,
):
    resp = await client.get(f"{BASE}/counts", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["draft"] >= 1
    assert data["pending_approval"] >= 1
    assert data["approved"] >= 1
    assert data["total"] == data["draft"] + data["pending_approval"] + data["approved"]


# ---- 2. GET /assets — pagination ------------------------------------------

async def test_list_assets_with_pagination(
    client, admin_headers, draft_asset,
):
    resp = await client.get(f"{BASE}", headers=admin_headers, params={"page": 1, "size": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


# ---- 3. GET /assets?status=draft — filter by status -----------------------

async def test_list_assets_filter_by_status(
    client, admin_headers, draft_asset, approved_asset,
):
    resp = await client.get(f"{BASE}", headers=admin_headers, params={"status": "draft"})
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        assert item["status"] == "draft"


# ---- 4. GET /assets/{id} — single asset -----------------------------------

async def test_get_asset_by_id(client, admin_headers, draft_asset):
    resp = await client.get(f"{BASE}/{draft_asset.id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(draft_asset.id)
    assert data["caption"] == "Test caption"


# ---- 5. GET /assets/{id} — nonexistent returns 404 ------------------------

async def test_get_asset_not_found(client, admin_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"{BASE}/{fake_id}", headers=admin_headers)
    assert resp.status_code == 404


# ---- 6. PATCH /assets/{id} — editor updates caption -----------------------

async def test_editor_can_update_caption(client, editor_headers, draft_asset):
    resp = await client.patch(
        f"{BASE}/{draft_asset.id}",
        headers=editor_headers,
        json={"caption": "Updated caption"},
    )
    assert resp.status_code == 200
    assert resp.json()["caption"] == "Updated caption"


# ---- 7. PATCH /assets/{id} — viewer gets 403 ------------------------------

async def test_viewer_cannot_update_asset(client, viewer_headers, draft_asset):
    resp = await client.patch(
        f"{BASE}/{draft_asset.id}",
        headers=viewer_headers,
        json={"caption": "Nope"},
    )
    assert resp.status_code == 403


# ---- 8. DELETE /assets/{id} — admin deletes (204) -------------------------

async def test_admin_can_delete_asset(client, admin_headers, draft_asset):
    resp = await client.delete(f"{BASE}/{draft_asset.id}", headers=admin_headers)
    assert resp.status_code == 204

    # Confirm it is gone
    resp2 = await client.get(f"{BASE}/{draft_asset.id}", headers=admin_headers)
    assert resp2.status_code == 404


# ---- 9. DELETE /assets/{id} — editor gets 403 -----------------------------

async def test_editor_cannot_delete_asset(client, editor_headers, draft_asset):
    resp = await client.delete(f"{BASE}/{draft_asset.id}", headers=editor_headers)
    assert resp.status_code == 403


# ---- 10. DELETE /assets/{id} — nonexistent returns 404 --------------------

async def test_delete_asset_not_found(client, admin_headers):
    fake_id = uuid.uuid4()
    resp = await client.delete(f"{BASE}/{fake_id}", headers=admin_headers)
    assert resp.status_code == 404
