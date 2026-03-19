"""Tests for the brand router."""

import uuid

import pytest



async def test_get_guidelines_returns_null_when_none_exist(client, admin_headers):
    resp = await client.get("/api/v1/brand/guidelines", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() is None


async def test_get_guidelines_returns_existing(client, admin_headers, brand_guideline):
    resp = await client.get("/api/v1/brand/guidelines", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["primary_colors"] == ["#2563EB", "#1E40AF"]
    assert data["fonts"] == ["Inter", "Roboto"]
    assert data["tone_description"] == "Professional, friendly, and concise"
    assert data["is_active"] is True


async def test_admin_creates_guidelines(client, admin_headers):
    payload = {
        "primary_colors": ["#FF0000"],
        "fonts": ["Arial"],
        "tone_description": "Bold and direct",
        "dos": ["Be concise"],
        "donts": ["Avoid slang"],
    }
    resp = await client.put(
        "/api/v1/brand/guidelines", json=payload, headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["primary_colors"] == ["#FF0000"]
    assert data["fonts"] == ["Arial"]
    assert data["tone_description"] == "Bold and direct"
    assert data["is_active"] is True
    assert "id" in data


async def test_admin_updates_existing_guidelines(client, admin_headers, brand_guideline):
    payload = {
        "primary_colors": ["#00FF00"],
        "tone_description": "Casual and fun",
    }
    resp = await client.put(
        "/api/v1/brand/guidelines", json=payload, headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    # Updated fields
    assert data["primary_colors"] == ["#00FF00"]
    assert data["tone_description"] == "Casual and fun"
    # Unchanged fields should remain
    assert data["fonts"] == ["Inter", "Roboto"]
    assert data["id"] == str(brand_guideline.id)


async def test_non_admin_cannot_update_guidelines(client, editor_headers):
    payload = {"primary_colors": ["#000000"]}
    resp = await client.put(
        "/api/v1/brand/guidelines", json=payload, headers=editor_headers
    )
    assert resp.status_code == 403


async def test_compliance_check_returns_400_when_no_guidelines(
    client, admin_headers, draft_asset
):
    resp = await client.post(
        f"/api/v1/brand/check/{draft_asset.id}", headers=admin_headers
    )
    assert resp.status_code == 400
    assert "guidelines" in resp.json()["detail"].lower()
