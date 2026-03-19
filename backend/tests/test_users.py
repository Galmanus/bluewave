"""Tests for the users router: /me, list, create, update, delete."""

import uuid

import pytest
from httpx import AsyncClient

PREFIX = "/api/v1/users"


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------


async def test_get_me(client: AsyncClient, admin_headers: dict):
    resp = await client.get(f"{PREFIX}/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


# ---------------------------------------------------------------------------
# GET /users  (list)
# ---------------------------------------------------------------------------


async def test_list_users_as_admin(client: AsyncClient, admin_headers: dict):
    resp = await client.get(PREFIX, headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1  # at least the admin user


async def test_list_users_as_viewer_forbidden(
    client: AsyncClient, viewer_headers: dict
):
    resp = await client.get(PREFIX, headers=viewer_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /users  (create)
# ---------------------------------------------------------------------------


def _new_user_payload(email: str | None = None) -> dict:
    return {
        "email": email or f"new-{uuid.uuid4().hex[:8]}@test.com",
        "password": "NewUser1!",
        "full_name": "Brand New User",
        "role": "editor",
    }


async def test_create_user_as_admin(client: AsyncClient, admin_headers: dict):
    payload = _new_user_payload()
    resp = await client.post(PREFIX, json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == payload["email"]
    assert data["role"] == "editor"
    assert "id" in data


async def test_create_user_duplicate_email(client: AsyncClient, admin_headers: dict):
    email = f"dup-{uuid.uuid4().hex[:8]}@test.com"
    payload = _new_user_payload(email)

    resp1 = await client.post(PREFIX, json=payload, headers=admin_headers)
    assert resp1.status_code == 201

    resp2 = await client.post(PREFIX, json=payload, headers=admin_headers)
    assert resp2.status_code == 409


async def test_create_user_as_viewer_forbidden(
    client: AsyncClient, viewer_headers: dict
):
    resp = await client.post(
        PREFIX, json=_new_user_payload(), headers=viewer_headers
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /users/{id}  (update role)
# ---------------------------------------------------------------------------


async def test_update_user_role(
    client: AsyncClient, admin_headers: dict, editor_user
):
    resp = await client.patch(
        f"{PREFIX}/{editor_user.id}",
        json={"role": "viewer"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"


# ---------------------------------------------------------------------------
# DELETE /users/{id}
# ---------------------------------------------------------------------------


async def test_delete_user_as_admin(client: AsyncClient, admin_headers: dict):
    # Create a disposable user first
    payload = _new_user_payload()
    create_resp = await client.post(PREFIX, json=payload, headers=admin_headers)
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    resp = await client.delete(f"{PREFIX}/{user_id}", headers=admin_headers)
    assert resp.status_code == 204


async def test_delete_self_forbidden(
    client: AsyncClient, admin_headers: dict, admin_user
):
    resp = await client.delete(
        f"{PREFIX}/{admin_user.id}", headers=admin_headers
    )
    assert resp.status_code == 400
    assert "yourself" in resp.json()["detail"].lower()


async def test_delete_user_as_viewer_forbidden(
    client: AsyncClient, viewer_headers: dict, editor_user
):
    resp = await client.delete(
        f"{PREFIX}/{editor_user.id}", headers=viewer_headers
    )
    assert resp.status_code == 403
