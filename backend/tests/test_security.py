"""Tests for security: authentication, authorization, and password hashing."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import hash_password



async def test_no_auth_header_returns_401(client):
    """Protected endpoints reject requests without an Authorization header."""
    resp = await client.get("/api/v1/assets")
    assert resp.status_code == 401


async def test_expired_jwt_returns_401(client, admin_user, tenant):
    """An expired JWT is rejected with 401."""
    token = jwt.encode(
        {
            "sub": str(admin_user.id),
            "tenant_id": str(tenant.id),
            "role": "admin",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    resp = await client.get(
        "/api/v1/assets", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


async def test_invalid_jwt_returns_401(client):
    """A completely invalid JWT string is rejected with 401."""
    resp = await client.get(
        "/api/v1/assets",
        headers={"Authorization": "Bearer this-is-not-a-valid-jwt"},
    )
    assert resp.status_code == 401


async def test_viewer_cannot_post_assets(client, viewer_headers):
    """Viewer role cannot POST /assets (requires editor or admin)."""
    resp = await client.post(
        "/api/v1/assets",
        headers=viewer_headers,
        files={"file": ("test.jpg", b"fake-image-data", "image/jpeg")},
    )
    assert resp.status_code == 403


async def test_editor_cannot_delete_assets(client, editor_headers, draft_asset):
    """Editor role cannot DELETE /assets/{id} (requires admin)."""
    resp = await client.delete(
        f"/api/v1/assets/{draft_asset.id}", headers=editor_headers
    )
    assert resp.status_code == 403


async def test_admin_can_do_everything(client, admin_headers, draft_asset):
    """Admin role can access all endpoints."""
    # GET assets
    resp = await client.get("/api/v1/assets", headers=admin_headers)
    assert resp.status_code == 200

    # GET single asset
    resp = await client.get(
        f"/api/v1/assets/{draft_asset.id}", headers=admin_headers
    )
    assert resp.status_code == 200

    # DELETE asset
    resp = await client.delete(
        f"/api/v1/assets/{draft_asset.id}", headers=admin_headers
    )
    assert resp.status_code == 204


async def test_bcrypt_hash_not_reversible():
    """hash_password returns a different hash each time (unique salts)."""
    password = "MySecretP@ss123"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2
    assert hash1 != password
    assert hash2 != password
    assert hash1.startswith("$2b$")
    assert hash2.startswith("$2b$")
