"""Tests for the webhooks router."""

import uuid

import pytest



async def test_admin_lists_webhooks(client, admin_headers, webhook):
    resp = await client.get("/api/v1/webhooks", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["name"] == "Test Webhook"
    assert data[0]["url"] == "https://example.com/webhook"


async def test_non_admin_cannot_list_webhooks(client, editor_headers):
    resp = await client.get("/api/v1/webhooks", headers=editor_headers)
    assert resp.status_code == 403


async def test_admin_creates_webhook(client, admin_headers):
    payload = {"name": "My Hook", "url": "https://example.com/hook", "events": "*"}
    resp = await client.post("/api/v1/webhooks", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Hook"
    assert data["url"] == "https://example.com/hook"
    assert data["events"] == "*"
    assert data["is_active"] is True
    assert "id" in data


async def test_admin_updates_webhook(client, admin_headers, webhook):
    resp = await client.patch(
        f"/api/v1/webhooks/{webhook.id}",
        json={"name": "Updated Hook", "is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Hook"
    assert data["is_active"] is False


async def test_update_nonexistent_webhook_returns_404(client, admin_headers):
    fake_id = uuid.uuid4()
    resp = await client.patch(
        f"/api/v1/webhooks/{fake_id}",
        json={"name": "Ghost"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


async def test_admin_deletes_webhook(client, admin_headers, webhook):
    resp = await client.delete(
        f"/api/v1/webhooks/{webhook.id}", headers=admin_headers
    )
    assert resp.status_code == 204

    # Confirm it's gone
    resp = await client.get("/api/v1/webhooks", headers=admin_headers)
    ids = [w["id"] for w in resp.json()]
    assert str(webhook.id) not in ids
