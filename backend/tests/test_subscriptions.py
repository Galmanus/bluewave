"""Tests for the billing/subscriptions router."""

import pytest



async def test_get_plan_returns_summary(client, admin_headers):
    """GET /billing/plan returns plan summary and auto-creates free tier subscription."""
    resp = await client.get("/api/v1/billing/plan", headers=admin_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["plan"]["plan"] == "free"
    assert data["plan"]["is_active"] is True


async def test_get_plan_has_correct_structure(client, admin_headers):
    """GET /billing/plan response contains both plan and usage sections with expected keys."""
    resp = await client.get("/api/v1/billing/plan", headers=admin_headers)
    assert resp.status_code == 200

    data = resp.json()

    # Plan section
    plan = data["plan"]
    assert "plan" in plan
    assert "is_active" in plan
    assert "max_users" in plan
    assert "max_ai_actions_month" in plan
    assert "max_storage_bytes" in plan
    assert "current_period_start" in plan
    assert "current_period_end" in plan
    assert "stripe_customer_id" in plan

    # Usage section
    usage = data["usage"]
    assert "ai_actions_used" in usage
    assert "ai_actions_limit" in usage
    assert "storage_used_bytes" in usage
    assert "storage_limit_bytes" in usage
    assert "users_count" in usage
    assert "users_limit" in usage

    # Usage limits should match plan limits
    assert usage["ai_actions_limit"] == plan["max_ai_actions_month"]
    assert usage["storage_limit_bytes"] == plan["max_storage_bytes"]
    assert usage["users_limit"] == plan["max_users"]


async def test_get_usage_returns_stats(client, admin_headers):
    """GET /billing/usage returns usage stats."""
    resp = await client.get("/api/v1/billing/usage", headers=admin_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["ai_actions_used"] >= 0
    assert data["ai_actions_limit"] > 0
    assert data["storage_used_bytes"] >= 0
    assert data["storage_limit_bytes"] > 0
    assert data["users_count"] >= 1  # at least the admin user exists
    assert data["users_limit"] > 0
