"""Unit tests for the compliance service."""

from unittest.mock import MagicMock

from app.services.compliance_service import (
    ComplianceResult,
    _build_guidelines_prompt,
    check_compliance,
)


def test_build_guidelines_prompt():
    """Guidelines prompt includes all non-empty fields."""
    guidelines = MagicMock()
    guidelines.primary_colors = ["#FF0000"]
    guidelines.secondary_colors = None
    guidelines.fonts = ["Inter"]
    guidelines.tone_description = "Professional"
    guidelines.dos = ["Be clear"]
    guidelines.donts = ["Don't ramble"]
    guidelines.custom_rules = None

    prompt = _build_guidelines_prompt(guidelines)
    assert "#FF0000" in prompt
    assert "Inter" in prompt
    assert "Professional" in prompt
    assert "Be clear" in prompt
    assert "Don't ramble" in prompt


async def test_compliance_no_api_key_returns_default():
    """Without ANTHROPIC_API_KEY, compliance returns 100 score (pass)."""
    from unittest.mock import patch

    guidelines = MagicMock()

    with patch("app.services.compliance_service.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = ""
        result = await check_compliance(
            file_path=None,
            file_type="image/jpeg",
            caption="Test caption",
            hashtags=["#test"],
            guidelines=guidelines,
        )

    assert isinstance(result, ComplianceResult)
    assert result.score == 100
    assert result.passed is True
