"""Tests for the auth router: register, login, refresh, logout, password reset."""

import uuid

import pytest
from httpx import AsyncClient

PREFIX = "/api/v1/auth"


def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@test.com"


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


async def test_register_happy_path(client: AsyncClient):
    email = unique_email()
    resp = await client.post(
        f"{PREFIX}/register",
        json={
            "tenant_name": "New Corp",
            "email": email,
            "password": "Str0ngPass!",
            "full_name": "New User",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "tenant_id" in data
    assert "user_id" in data


async def test_register_duplicate_email(client: AsyncClient):
    email = unique_email()
    payload = {
        "tenant_name": "Dup Corp",
        "email": email,
        "password": "Str0ngPass!",
        "full_name": "Dup User",
    }
    resp1 = await client.post(f"{PREFIX}/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post(f"{PREFIX}/register", json=payload)
    assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def _register_and_get_email(client: AsyncClient, password: str = "Login123!") -> str:
    """Helper: register a fresh user and return its email."""
    email = unique_email()
    resp = await client.post(
        f"{PREFIX}/register",
        json={
            "tenant_name": "Login Corp",
            "email": email,
            "password": password,
            "full_name": "Login User",
        },
    )
    assert resp.status_code == 201
    return email


async def test_login_happy_path(client: AsyncClient):
    password = "Login123!"
    email = await _register_and_get_email(client, password)

    resp = await client.post(
        f"{PREFIX}/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Refresh token should be set as a cookie
    assert "refresh_token" in resp.cookies


async def test_login_wrong_password(client: AsyncClient):
    email = await _register_and_get_email(client)

    resp = await client.post(
        f"{PREFIX}/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_email(client: AsyncClient):
    resp = await client.post(
        f"{PREFIX}/login",
        json={"email": "nobody@nowhere.com", "password": "Whatever1"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


async def test_refresh_happy_path(client: AsyncClient):
    password = "Refresh1!"
    email = await _register_and_get_email(client, password)

    # Login to get the refresh cookie
    login_resp = await client.post(
        f"{PREFIX}/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200

    # The client jar should now contain the refresh_token cookie.
    # httpx AsyncClient automatically sends stored cookies.
    refresh_resp = await client.post(f"{PREFIX}/refresh")
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


async def test_refresh_no_cookie(client: AsyncClient):
    # Fresh client request with no cookies at all
    resp = await client.post(f"{PREFIX}/refresh")
    # Depending on whether previous tests left a cookie in the jar,
    # we clear cookies to ensure a clean state.
    client.cookies.clear()
    resp = await client.post(f"{PREFIX}/refresh")
    assert resp.status_code == 401


async def test_refresh_invalid_token(client: AsyncClient):
    client.cookies.clear()
    client.cookies.set("refresh_token", "not-a-valid-jwt")
    resp = await client.post(f"{PREFIX}/refresh")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def test_logout_clears_cookie(client: AsyncClient):
    resp = await client.post(f"{PREFIX}/logout")
    assert resp.status_code == 204
    # The response should instruct the browser to delete the cookie
    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "refresh_token" in set_cookie_header


# ---------------------------------------------------------------------------
# Reset password request
# ---------------------------------------------------------------------------


async def test_reset_password_request_returns_token(client: AsyncClient):
    password = "Reset123!"
    email = await _register_and_get_email(client, password)

    resp = await client.post(
        f"{PREFIX}/reset-password-request",
        json={"email": email},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    # In dev mode the reset_token is returned directly
    assert "reset_token" in data


async def test_reset_password_request_nonexistent_email(client: AsyncClient):
    resp = await client.post(
        f"{PREFIX}/reset-password-request",
        json={"email": "ghost@nowhere.com"},
    )
    # Should still return 200 to prevent email enumeration
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    # No reset_token for unknown emails
    assert "reset_token" not in data


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------


async def test_reset_password_happy_path(client: AsyncClient):
    password = "OldPass1!"
    email = await _register_and_get_email(client, password)

    # Request a reset token
    req_resp = await client.post(
        f"{PREFIX}/reset-password-request",
        json={"email": email},
    )
    reset_token = req_resp.json()["reset_token"]

    # Use the token to set a new password
    new_password = "NewPass1!"
    resp = await client.post(
        f"{PREFIX}/reset-password",
        json={"token": reset_token, "new_password": new_password},
    )
    assert resp.status_code == 200

    # Verify the new password works for login
    login_resp = await client.post(
        f"{PREFIX}/login",
        json={"email": email, "password": new_password},
    )
    assert login_resp.status_code == 200


async def test_reset_password_invalid_token(client: AsyncClient):
    resp = await client.post(
        f"{PREFIX}/reset-password",
        json={"token": "invalid-jwt-token", "new_password": "NewPass1!"},
    )
    assert resp.status_code == 401
