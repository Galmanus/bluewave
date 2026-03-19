"""Unit tests for AI service: StubAIService + ClaudeAIService (mocked)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_service import StubAIService


# ---------------------------------------------------------------------------
# StubAIService — deterministic responses
# ---------------------------------------------------------------------------


async def test_stub_caption_image():
    svc = StubAIService()
    caption = await svc.generate_caption("hero.jpg", "image/jpeg")
    assert "hero.jpg" in caption
    assert "visual" in caption.lower()


async def test_stub_caption_video():
    svc = StubAIService()
    caption = await svc.generate_caption("promo.mp4", "video/mp4")
    assert "promo.mp4" in caption
    assert "video" in caption.lower()


async def test_stub_hashtags_image():
    svc = StubAIService()
    tags = await svc.generate_hashtags("photo.png", "image/png")
    assert isinstance(tags, list)
    assert all(t.startswith("#") for t in tags)
    assert "#photography" in tags


async def test_stub_hashtags_video():
    svc = StubAIService()
    tags = await svc.generate_hashtags("clip.mov", "video/quicktime")
    assert isinstance(tags, list)
    assert "#videocontent" in tags


# ---------------------------------------------------------------------------
# ClaudeAIService — mocked anthropic client
# ---------------------------------------------------------------------------


async def test_claude_caption_calls_api():
    """ClaudeAIService.generate_caption calls Anthropic API and returns text."""
    from app.services.ai_service import ClaudeAIService

    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="A beautiful sunset over the mountains")]

    with patch.object(ClaudeAIService, "__init__", lambda self: None):
        svc = ClaudeAIService()
        svc._client = MagicMock()
        svc._client.messages.create = AsyncMock(return_value=mock_resp)
        svc._model = "test-model"

        caption = await svc.generate_caption(
            "sunset.jpg", "image/jpeg", file_path=None, tenant_id=None
        )

    assert caption == "A beautiful sunset over the mountains"
    svc._client.messages.create.assert_awaited_once()


async def test_claude_hashtags_parses_json():
    """ClaudeAIService.generate_hashtags parses JSON array from response."""
    from app.services.ai_service import ClaudeAIService

    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text='["#sunset", "#nature", "#photography"]')]

    with patch.object(ClaudeAIService, "__init__", lambda self: None):
        svc = ClaudeAIService()
        svc._client = MagicMock()
        svc._client.messages.create = AsyncMock(return_value=mock_resp)
        svc._model = "test-model"

        tags = await svc.generate_hashtags("sunset.jpg", "image/jpeg")

    assert tags == ["#sunset", "#nature", "#photography"]


async def test_claude_caption_fallback_on_error():
    """ClaudeAIService returns fallback caption when API errors."""
    from app.services.ai_service import ClaudeAIService

    with patch.object(ClaudeAIService, "__init__", lambda self: None):
        svc = ClaudeAIService()
        svc._client = MagicMock()
        svc._client.messages.create = AsyncMock(side_effect=Exception("API error"))
        svc._model = "test-model"

        caption = await svc.generate_caption("file.jpg", "image/jpeg")

    assert "file.jpg" in caption


async def test_claude_hashtags_fallback_on_error():
    """ClaudeAIService returns fallback hashtags when API errors."""
    from app.services.ai_service import ClaudeAIService

    with patch.object(ClaudeAIService, "__init__", lambda self: None):
        svc = ClaudeAIService()
        svc._client = MagicMock()
        svc._client.messages.create = AsyncMock(side_effect=Exception("API error"))
        svc._model = "test-model"

        tags = await svc.generate_hashtags("file.jpg", "image/jpeg")

    assert isinstance(tags, list)
    assert len(tags) > 0
    assert all(t.startswith("#") for t in tags)
