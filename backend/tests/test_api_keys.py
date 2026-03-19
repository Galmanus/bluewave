"""Tests for the api_keys router."""

import pytest



async def test_admin_creates_api_key(client, admin_headers):
    resp = await client.post(
        "/api/v1/api-keys", json={"name": "CI Key"}, headers=admin_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "CI Key"
    assert "key" in data
    assert len(data["key"]) > 0
    assert "key_prefix" in data
    assert "id" in data


async def test_admin_lists_api_keys(client, admin_headers):
    # Create a key first so the list is non-empty
    await client.post(
        "/api/v1/api-keys", json={"name": "CI Key"}, headers=admin_headers
    )

    resp = await client.get("/api/v1/api-keys", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # key_hash must NOT be exposed in the list response
    for key_entry in data:
        assert "key_hash" not in key_entry
        assert "key_prefix" in key_entry


async def test_admin_revokes_api_key(client, admin_headers):
    # Create then revoke
    create_resp = await client.post(
        "/api/v1/api-keys", json={"name": "CI Key"}, headers=admin_headers
    )
    key_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/api-keys/{key_id}", headers=admin_headers
    )
    assert resp.status_code == 204


async def test_non_admin_cannot_create_api_key(client, editor_headers):
    resp = await client.post(
        "/api/v1/api-keys", json={"name": "CI Key"}, headers=editor_headers
    )
    assert resp.status_code == 403


async def test_non_admin_cannot_list_api_keys(client, editor_headers):
    resp = await client.get("/api/v1/api-keys", headers=editor_headers)
    assert resp.status_code == 403
