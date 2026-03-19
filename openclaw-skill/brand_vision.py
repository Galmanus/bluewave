"""Direct brand compliance analysis via Claude Vision.

Bypasses the orchestrator for maximum efficiency:
- Loads brand DNA from Bluewave API
- Sends image + brand rules directly to Claude Vision (Haiku)
- Returns structured compliance report
- Cost: ~$0.005 per analysis (Haiku Vision)
"""

import base64
import json
import logging
import os

import anthropic
import httpx

logger = logging.getLogger("openclaw.brand_vision")

HAIKU = "claude-haiku-4-5-20251001"


async def get_brand_guidelines() -> dict | None:
    """Fetch brand guidelines from Bluewave API."""
    api_url = os.environ.get("BLUEWAVE_API_URL", "http://localhost:8300/api/v1")
    api_key = os.environ.get("BLUEWAVE_API_KEY", "")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{api_url}/brand/guidelines",
                headers={"X-API-Key": api_key},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if data else None
    except Exception as e:
        logger.error("Failed to fetch brand guidelines: %s", e)
    return None


def build_brand_prompt(guidelines: dict) -> str:
    """Build a concise brand rules prompt from guidelines."""
    parts = []

    brand_name = (guidelines.get("custom_rules") or {}).get("brand_name", "the brand")
    parts.append(f"BRAND: {brand_name}")

    if guidelines.get("primary_colors"):
        parts.append(f"PRIMARY COLORS: {', '.join(guidelines['primary_colors'])}")
    if guidelines.get("secondary_colors"):
        parts.append(f"SECONDARY COLORS: {', '.join(guidelines['secondary_colors'][:6])}")
    if guidelines.get("fonts"):
        parts.append(f"FONTS: {', '.join(guidelines['fonts'])}")
    if guidelines.get("tone_description"):
        parts.append(f"TONE: {guidelines['tone_description'][:200]}")
    if guidelines.get("dos"):
        parts.append("DO: " + " | ".join(guidelines["dos"]))
    if guidelines.get("donts"):
        parts.append("DON'T: " + " | ".join(guidelines["donts"]))

    custom = guidelines.get("custom_rules") or {}
    if custom.get("positioning"):
        parts.append(f"POSITIONING: {custom['positioning']}")
    if custom.get("photography_style"):
        parts.append(f"PHOTO STYLE: {custom['photography_style']}")

    return "\n".join(parts)


async def analyze_brand_compliance(image_b64: str, media_type: str = "image/jpeg") -> str:
    """Analyze an image against brand guidelines using Claude Vision directly.

    Returns a formatted compliance report.
    Cost: ~$0.005 with Haiku Vision.
    """
    guidelines = await get_brand_guidelines()

    if not guidelines:
        return "No brand guidelines configured. Go to Brand page to set up your Brand DNA first."

    brand_rules = build_brand_prompt(guidelines)
    brand_name = (guidelines.get("custom_rules") or {}).get("brand_name", "the brand")

    client = anthropic.Anthropic()

    system_prompt = (
        f"You are a brand compliance analyst for {brand_name}. "
        "Analyze the image against the brand rules below. "
        "Be specific about what matches and what violates. "
        "Give a score 0-100. List each issue with severity (critical/warning/info). "
        "Suggest specific fixes for each issue. "
        "Be concise and actionable. Respond in the same language as the brand rules."
    )

    try:
        response = client.messages.create(
            model=HAIKU,
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Analyze this image for brand compliance.\n\nBRAND RULES:\n{brand_rules}",
                        },
                    ],
                }
            ],
        )

        return response.content[0].text

    except Exception as e:
        logger.error("Brand vision analysis failed: %s", e)
        return f"Analysis failed: {str(e)[:100]}"
