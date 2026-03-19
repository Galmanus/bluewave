"""Tests for the Bluewave OpenClaw skill handler.

Run: python -m pytest test_handler.py -v
"""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

# Set env before import
import os
os.environ["BLUEWAVE_API_URL"] = "http://test:8000/api/v1"
os.environ["BLUEWAVE_API_KEY"] = "bw_test_key_123"

from handler import BlueWaveHandler, format_webhook_event, ToolResult


@pytest.fixture
def handler():
    return BlueWaveHandler(
        api_url="http://test:8000/api/v1",
        api_key="bw_test_key_123",
    )


def mock_response(status_code=200, json_data=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
        resp.text = json.dumps(json_data or {"detail": "error"})
    return resp


# ── List Assets ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_assets(handler):
    mock_data = {
        "items": [
            {"id": "abc-123", "caption": "Test caption", "status": "draft",
             "file_type": "image/png", "file_size": 1024},
        ],
        "total": 1, "page": 1, "size": 20,
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_list_assets", {})
        assert result.success
        assert "1 assets" in result.message
        assert "abc-123" in result.message


@pytest.mark.asyncio
async def test_list_assets_empty(handler):
    mock_data = {"items": [], "total": 0, "page": 1, "size": 20}
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_list_assets", {})
        assert result.success
        assert "No assets found" in result.message


# ── Get Asset ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_asset(handler):
    mock_data = {
        "id": "abc-123", "caption": "Beautiful sunset",
        "hashtags": ["#sunset", "#nature"], "status": "approved",
        "file_type": "image/jpeg", "file_size": 2048,
        "compliance_score": 95, "rejection_comment": None,
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_get_asset", {"asset_id": "abc-123"})
        assert result.success
        assert "Beautiful sunset" in result.message
        assert "approved" in result.message
        assert "95/100" in result.message


# ── Workflow ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_for_approval(handler):
    mock_data = {"id": "abc-123", "status": "pending_approval"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_submit_for_approval", {"asset_id": "abc-123"})
        assert result.success
        assert "submitted" in result.message


@pytest.mark.asyncio
async def test_approve_asset(handler):
    mock_data = {"id": "abc-123", "status": "approved"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_approve_asset", {"asset_id": "abc-123"})
        assert result.success
        assert "approved" in result.message.lower()


@pytest.mark.asyncio
async def test_reject_asset(handler):
    mock_data = {"id": "abc-123", "status": "draft"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_reject_asset", {
            "asset_id": "abc-123", "comment": "Too dark"
        })
        assert result.success
        assert "Too dark" in result.message


# ── AI ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_usage(handler):
    mock_data = {
        "total_actions": 42, "total_cost_cents": 2.10,
        "actions_by_type": {"caption": 20, "hashtags": 22},
        "period_start": "2026-03-01", "period_end": "2026-03-18",
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_ai_usage", {"days": 30})
        assert result.success
        assert "42" in result.message
        assert "$2.10" in result.message


# ── Team ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_team(handler):
    mock_data = [
        {"full_name": "Jane Admin", "email": "jane@test.com", "role": "admin"},
        {"full_name": "Bob Editor", "email": "bob@test.com", "role": "editor"},
    ]
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_list_team", {})
        assert result.success
        assert "Jane Admin" in result.message
        assert "2 members" in result.message


# ── Error Handling ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_unknown_tool(handler):
    result = await handler.execute("bluewave_nonexistent", {})
    assert not result.success
    assert "Unknown tool" in result.message


@pytest.mark.asyncio
async def test_api_error(handler):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(404, {"detail": "Asset not found"})):
        result = await handler.execute("bluewave_get_asset", {"asset_id": "bad-id"})
        assert not result.success
        assert "404" in result.message


@pytest.mark.asyncio
async def test_connection_error(handler):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=httpx.ConnectError("Connection refused")):
        result = await handler.execute("bluewave_list_assets", {})
        assert not result.success
        assert "Cannot connect" in result.message


# ── Webhook Formatter ────────────────────────────────────────

def test_format_asset_uploaded():
    msg = format_webhook_event("asset.uploaded", {
        "file_type": "image/png", "file_size": 2048, "uploaded_by": "user-1"
    })
    assert "New asset uploaded" in msg
    assert "image/png" in msg


def test_format_asset_approved():
    msg = format_webhook_event("asset.approved", {
        "id": "abc-12345678", "caption": "Great shot"
    })
    assert "approved" in msg.lower()
    assert "abc-1234" in msg


def test_format_asset_rejected():
    msg = format_webhook_event("asset.rejected", {
        "id": "abc-12345678", "rejection_comment": "Too blurry"
    })
    assert "rejected" in msg.lower()
    assert "Too blurry" in msg


def test_format_unknown_event():
    msg = format_webhook_event("custom.event", {"key": "value"})
    assert "custom.event" in msg


def test_no_api_key_raises(monkeypatch):
    import handler as handler_mod
    monkeypatch.setattr(handler_mod, "BLUEWAVE_API_KEY", "")
    with pytest.raises(ValueError, match="BLUEWAVE_API_KEY"):
        BlueWaveHandler(api_key="")


# ══════════════════════════════════════════════════════════════
# Enhanced tools tests
# ══════════════════════════════════════════════════════════════


# ── Asset Curator: search_assets ─────────────────────────────

@pytest.mark.asyncio
async def test_search_assets_with_results(handler):
    mock_data = {
        "items": [
            {"id": "img-001", "caption": "Sunset over the ocean", "status": "approved",
             "filename": "sunset.jpg", "compliance_score": 92},
            {"id": "img-002", "caption": "Sunrise at the lake", "status": "draft",
             "filename": "sunrise.png", "compliance_score": 78},
        ],
        "total": 2,
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_search_assets", {"query": "sunset"})
        assert result.success
        assert "2 results" in result.message
        assert "sunset" in result.message.lower()
        assert "sunset.jpg" in result.message


@pytest.mark.asyncio
async def test_search_assets_empty(handler):
    mock_data = {"items": [], "total": 0}
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_search_assets", {"query": "nonexistent"})
        assert result.success
        assert "No assets found" in result.message
        assert "nonexistent" in result.message


# ── Asset Curator: bulk_export ───────────────────────────────

@pytest.mark.asyncio
async def test_bulk_export_success(handler):
    mock_data = {"download_url": "https://cdn.bluewave.io/exports/pack-abc123.zip"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_bulk_export", {
            "asset_ids": ["img-001", "img-002", "img-003"]
        })
        assert result.success
        assert "3 assets" in result.message
        assert "pack-abc123.zip" in result.message


# ── Asset Curator: asset_variants ────────────────────────────

@pytest.mark.asyncio
async def test_asset_variants_with_variants(handler):
    mock_data = [
        {"label": "Thumbnail", "width": 150, "height": 150, "file_size": 8192},
        {"label": "Instagram Square", "width": 1080, "height": 1080, "file_size": 524288},
        {"label": "Twitter Banner", "width": 1500, "height": 500, "file_size": 262144},
    ]
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_asset_variants", {"asset_id": "img-001"})
        assert result.success
        assert "3 variants" in result.message
        assert "Thumbnail" in result.message
        assert "1080x1080" in result.message


@pytest.mark.asyncio
async def test_asset_variants_empty(handler):
    mock_data = []
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_asset_variants", {"asset_id": "img-099"})
        assert result.success
        assert "No resize variants" in result.message


# ── Workflow Director: batch_approve ─────────────────────────

@pytest.mark.asyncio
async def test_batch_approve_partial_success(handler):
    call_count = 0

    async def side_effect_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            # Second call fails
            resp = mock_response(400, {"detail": "Not in pending state"})
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=MagicMock(), response=resp
            )
            resp.raise_for_status()
        return mock_response(json_data={"status": "approved"})

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=side_effect_post):
        result = await handler.execute("bluewave_batch_approve", {
            "asset_ids": ["img-001", "img-002", "img-003"]
        })
        assert result.success
        assert "2/3 succeeded" in result.message
        assert "Failed: 1" in result.message


# ── Workflow Director: workflow_stats ────────────────────────

@pytest.mark.asyncio
async def test_workflow_stats(handler):
    mock_data = {
        "pending_count": 12,
        "avg_approval_hours": 4.5,
        "approval_rate": 82,
        "rejection_rate": 18,
        "by_status": {"draft": 30, "pending_approval": 12, "approved": 156},
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_workflow_stats", {"days": 30})
        assert result.success
        assert "Pending: **12**" in result.message
        assert "4.5h" in result.message
        assert "82%" in result.message


# ── Workflow Director: auto_approve_by_score ─────────────────

@pytest.mark.asyncio
async def test_auto_approve_by_score(handler):
    list_data = {
        "items": [
            {"id": "asset-aaa", "compliance_score": 95, "status": "pending_approval"},
            {"id": "asset-bbb", "compliance_score": 60, "status": "pending_approval"},
            {"id": "asset-ccc", "compliance_score": 92, "status": "pending_approval"},
        ],
        "total": 3,
    }
    approve_resp = mock_response(json_data={"status": "approved"})

    async def mock_get(*args, **kwargs):
        return mock_response(json_data=list_data)

    async def mock_post(*args, **kwargs):
        return approve_resp

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_get):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_post):
            result = await handler.execute("bluewave_auto_approve_by_score", {"min_score": 90})
            assert result.success
            # 2 eligible (95 and 92), 1 skipped (60)
            assert "2/3" in result.message
            assert "Approved: 2" in result.message
            assert "Skipped" in result.message


# ── Brand Guardian: update_brand_guidelines ──────────────────

@pytest.mark.asyncio
async def test_update_brand_guidelines(handler):
    mock_data = {"colors": ["#FF6B00", "#1A1A2E"], "tone": "professional"}
    with patch("httpx.AsyncClient.put", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_update_brand_guidelines", {
            "colors": ["#FF6B00", "#1A1A2E"], "tone": "professional"
        })
        assert result.success
        assert "colors" in result.message
        assert "tone" in result.message
        assert "updated" in result.message.lower()


# ── Brand Guardian: compliance_report ────────────────────────

@pytest.mark.asyncio
async def test_compliance_report(handler):
    mock_data = {
        "avg_score": 84,
        "pass_rate": 76,
        "total_checks": 210,
        "top_issues": [
            {"category": "color_mismatch", "count": 35},
            {"category": "font_violation", "count": 12},
        ],
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_compliance_report", {"days": 30})
        assert result.success
        assert "84/100" in result.message
        assert "76%" in result.message
        assert "210" in result.message
        assert "color_mismatch" in result.message


# ── Brand Guardian: check_external_image ─────────────────────

@pytest.mark.asyncio
async def test_check_external_image_with_issues(handler):
    mock_data = {
        "score": 55,
        "passed": False,
        "summary": "Image has significant brand violations",
        "issues": [
            {"severity": "error", "category": "off_brand_color", "message": "Uses unapproved red (#FF0000)", "suggestion": "Use brand red #CC3333"},
            {"severity": "warning", "category": "low_resolution", "message": "Image is below 1080px width"},
        ],
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_check_external_image", {
            "image_url": "https://example.com/logo.png"
        })
        assert result.success
        assert "55/100" in result.message
        assert "FAIL" in result.message
        assert "off_brand_color" in result.message
        assert "low_resolution" in result.message


# ── Analytics Strategist: dashboard_metrics ──────────────────

@pytest.mark.asyncio
async def test_dashboard_metrics(handler):
    mock_data = {
        "volume": {"total_uploads": 340, "approved": 280},
        "speed": {"avg_approval_hours": 3.2},
        "efficiency": {"first_pass_rate": 78},
        "cost": {"ai_total": 12.50},
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_dashboard_metrics", {"days": 30})
        assert result.success
        assert "Dashboard" in result.message
        assert "Volume" in result.message
        assert "Speed" in result.message
        assert "total_uploads" in result.message


# ── Analytics Strategist: roi_report ─────────────────────────

@pytest.mark.asyncio
async def test_roi_report(handler):
    mock_data = {
        "hours_saved": 120.5,
        "value_generated": 6025.00,
        "platform_cost": 499.00,
        "roi_percentage": 1107,
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_roi_report", {"hourly_rate": 50})
        assert result.success
        assert "120.5h" in result.message
        assert "$6,025.00" in result.message
        assert "$499.00" in result.message
        assert "1107%" in result.message


# ── Analytics Strategist: trend_analysis ─────────────────────

@pytest.mark.asyncio
async def test_trend_analysis(handler):
    mock_data = {
        "trend": "increasing",
        "summary": "Upload volume grew 23% over the period",
        "data_points": [{"date": "2026-03-01", "value": 10}, {"date": "2026-03-08", "value": 15}],
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_trend_analysis", {"metric": "uploads", "days": 90})
        assert result.success
        assert "uploads" in result.message
        assert "increasing" in result.message
        assert "23%" in result.message
        assert "Data points: 2" in result.message


# ── Analytics Strategist: team_productivity ──────────────────

@pytest.mark.asyncio
async def test_team_productivity(handler):
    mock_data = {
        "members": [
            {"full_name": "Alice Designer", "uploads": 45, "approvals": 0},
            {"full_name": "Bob Manager", "uploads": 3, "approvals": 62},
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_team_productivity", {"days": 30})
        assert result.success
        assert "Alice Designer" in result.message
        assert "45 uploads" in result.message
        assert "Bob Manager" in result.message
        assert "62 approvals" in result.message


# ── Creative Strategist: generate_brief ──────────────────────

@pytest.mark.asyncio
async def test_generate_brief(handler):
    mock_data = {
        "brief": "## Product Launch Campaign\n\nObjective: Drive awareness for the new summer line.\n\nChannels: Instagram, TikTok\nTone: Energetic, youthful\n\nKey messages:\n- Fresh styles for summer 2026\n- Limited edition colorways"
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_generate_brief", {
            "prompt": "Summer product launch", "channels": ["instagram", "tiktok"], "tone": "energetic"
        })
        assert result.success
        assert "Creative Brief" in result.message
        assert "Product Launch Campaign" in result.message


# ── Creative Strategist: caption_variants ────────────────────

@pytest.mark.asyncio
async def test_caption_variants(handler):
    mock_data = {
        "variants": [
            {"tone": "professional", "caption": "Elevate your workflow with our latest features."},
            {"tone": "casual", "caption": "Check this out - you're gonna love what we just shipped!"},
            {"tone": "witty", "caption": "Your competitors called. They want to know your secret."},
        ]
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_caption_variants", {
            "asset_id": "img-001", "tones": ["professional", "casual", "witty"]
        })
        assert result.success
        assert "3 caption variants" in result.message
        assert "Professional" in result.message
        assert "Casual" in result.message
        assert "competitors" in result.message


# ── Creative Strategist: translate_caption ───────────────────

@pytest.mark.asyncio
async def test_translate_caption(handler):
    mock_data = {
        "translations": {
            "es": "Eleva tu flujo de trabajo con nuestras funciones.",
            "fr": "Optimisez votre flux de travail avec nos fonctionnalites.",
            "pt": "Eleve seu fluxo de trabalho com nossos recursos.",
        }
    }
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_translate_caption", {
            "asset_id": "img-001", "languages": ["es", "fr", "pt"]
        })
        assert result.success
        assert "Translations" in result.message
        assert "ES:" in result.message
        assert "FR:" in result.message
        assert "flujo de trabajo" in result.message


# ── Creative Strategist: content_calendar ────────────────────

@pytest.mark.asyncio
async def test_content_calendar(handler):
    mock_data = {
        "events": [
            {"scheduled_at": "2026-03-20T10:00:00Z", "channel": "instagram", "caption": "Spring collection drop"},
            {"scheduled_at": "2026-03-22T14:30:00Z", "channel": "twitter", "caption": "Behind the scenes"},
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_content_calendar", {
            "start": "2026-03-18", "end": "2026-03-31"
        })
        assert result.success
        assert "Content Calendar" in result.message
        assert "instagram" in result.message
        assert "Spring collection" in result.message


# ── Creative Strategist: schedule_post ───────────────────────

@pytest.mark.asyncio
async def test_schedule_post(handler):
    mock_data = {"id": "post-777", "status": "scheduled"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_schedule_post", {
            "asset_id": "img-001",
            "scheduled_at": "2026-03-25T09:00:00Z",
            "channel": "instagram",
        })
        assert result.success
        assert "scheduled" in result.message.lower()
        assert "instagram" in result.message
        assert "2026-03-25" in result.message


# ── Ops Admin: remove_user ───────────────────────────────────

@pytest.mark.asyncio
async def test_remove_user(handler):
    with patch("httpx.AsyncClient.delete", new_callable=AsyncMock, return_value=mock_response(json_data={})):
        result = await handler.execute("bluewave_remove_user", {"user_id": "usr-dead-beef"})
        assert result.success
        assert "removed" in result.message.lower()


# ── Ops Admin: update_user_role ──────────────────────────────

@pytest.mark.asyncio
async def test_update_user_role(handler):
    mock_data = {"id": "usr-abc", "full_name": "Carol Viewer", "role": "editor"}
    with patch("httpx.AsyncClient.patch", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_update_user_role", {
            "user_id": "usr-abc", "new_role": "editor"
        })
        assert result.success
        assert "Carol Viewer" in result.message
        assert "editor" in result.message


# ── Ops Admin: billing_summary ───────────────────────────────

@pytest.mark.asyncio
async def test_billing_summary(handler):
    mock_data = {
        "plan": "Business",
        "seats_used": 8,
        "seats_total": 15,
        "monthly_cost": 299.00,
        "ai_cost": 14.75,
        "next_billing": "2026-04-01",
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_billing_summary", {})
        assert result.success
        assert "Business" in result.message
        assert "8/15" in result.message
        assert "$299.00" in result.message
        assert "$14.75" in result.message
        assert "2026-04-01" in result.message


# ── Ops Admin: create_api_key ────────────────────────────────

@pytest.mark.asyncio
async def test_create_api_key(handler):
    mock_data = {"key": "bw_live_sk_9f8e7d6c5b4a", "name": "CI Pipeline"}
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_create_api_key", {
            "name": "CI Pipeline", "permissions": ["read", "write"]
        })
        assert result.success
        assert "CI Pipeline" in result.message
        assert "bw_live_sk_9f8e7d6c5b4a" in result.message
        assert "Save this key" in result.message


# ── Ops Admin: audit_log ────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log(handler):
    mock_data = {
        "entries": [
            {"timestamp": "2026-03-18T09:15:00Z", "user_name": "Jane Admin", "action": "approved", "target": "asset img-001"},
            {"timestamp": "2026-03-18T08:30:00Z", "user_name": "Bob Editor", "action": "uploaded", "target": "asset img-002"},
            {"timestamp": "2026-03-17T17:00:00Z", "user_name": "Jane Admin", "action": "rejected", "target": "asset img-003"},
        ]
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_audit_log", {"days": 7})
        assert result.success
        assert "Audit Log" in result.message
        assert "3 entries" in result.message
        assert "Jane Admin" in result.message
        assert "approved" in result.message


# ── Ops Admin: storage_usage ────────────────────────────────

@pytest.mark.asyncio
async def test_storage_usage(handler):
    mock_data = {
        "total_bytes": 5368709120,  # 5 GB
        "by_type": {
            "image/jpeg": 3221225472,
            "image/png": 1073741824,
            "video/mp4": 1073741824,
        },
        "asset_count": 1247,
    }
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response(json_data=mock_data)):
        result = await handler.execute("bluewave_storage_usage", {})
        assert result.success
        assert "Storage Usage" in result.message
        assert "1247" in result.message
        assert "image/jpeg" in result.message
