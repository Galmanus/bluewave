"""Tests for the workflow router — submit / approve / reject transitions."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import AssetStatus, MediaAsset


BASE = "/api/v1/assets"


# ---- 1. POST /assets/{id}/submit — draft → pending (editor) ---------------

async def test_editor_can_submit_draft(client, editor_headers, draft_asset):
    resp = await client.post(
        f"{BASE}/{draft_asset.id}/submit", headers=editor_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_approval"


# ---- 2. POST /assets/{id}/submit — non-draft returns 400 ------------------

async def test_submit_non_draft_returns_400(client, admin_headers, pending_asset):
    resp = await client.post(
        f"{BASE}/{pending_asset.id}/submit", headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "draft" in resp.json()["detail"].lower()


# ---- 3. POST /assets/{id}/submit — viewer gets 403 ------------------------

async def test_viewer_cannot_submit(client, viewer_headers, draft_asset):
    resp = await client.post(
        f"{BASE}/{draft_asset.id}/submit", headers=viewer_headers,
    )
    assert resp.status_code == 403


# ---- 4. POST /assets/{id}/approve — pending → approved (admin) ------------

async def test_admin_can_approve_pending(client, admin_headers, pending_asset):
    resp = await client.post(
        f"{BASE}/{pending_asset.id}/approve", headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


# ---- 5. POST /assets/{id}/approve — compliance < 70 returns 400 -----------

async def test_approve_low_compliance_returns_400(
    client, admin_headers, db_session: AsyncSession, tenant, admin_user,
):
    """A pending asset with compliance_score=50 cannot be approved."""
    asset = MediaAsset(
        tenant_id=tenant.id,
        uploaded_by=admin_user.id,
        file_path="/app/uploads/test/low_compliance.jpg",
        file_type="image/jpeg",
        file_size=1024,
        status=AssetStatus.pending_approval,
        caption="Low compliance",
        hashtags=["#low"],
        compliance_score=50,
    )
    db_session.add(asset)
    await db_session.commit()
    await db_session.refresh(asset)

    resp = await client.post(
        f"{BASE}/{asset.id}/approve", headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "compliance" in resp.json()["detail"].lower()


# ---- 6. POST /assets/{id}/approve — non-admin gets 403 --------------------

async def test_editor_cannot_approve(client, editor_headers, pending_asset):
    resp = await client.post(
        f"{BASE}/{pending_asset.id}/approve", headers=editor_headers,
    )
    assert resp.status_code == 403


# ---- 7. POST /assets/{id}/approve — non-pending returns 400 ---------------

async def test_approve_non_pending_returns_400(client, admin_headers, draft_asset):
    resp = await client.post(
        f"{BASE}/{draft_asset.id}/approve", headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "pending_approval" in resp.json()["detail"].lower()


# ---- 8. POST /assets/{id}/reject — pending → draft with comment (admin) ---

async def test_admin_can_reject_pending(client, admin_headers, pending_asset):
    resp = await client.post(
        f"{BASE}/{pending_asset.id}/reject",
        headers=admin_headers,
        json={"comment": "Needs better caption"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "draft"
    assert data["rejection_comment"] == "Needs better caption"


# ---- 9. POST /assets/{id}/reject — non-pending returns 400 ----------------

async def test_reject_non_pending_returns_400(client, admin_headers, draft_asset):
    resp = await client.post(
        f"{BASE}/{draft_asset.id}/reject",
        headers=admin_headers,
        json={"comment": "Should fail"},
    )
    assert resp.status_code == 400
    assert "pending_approval" in resp.json()["detail"].lower()
