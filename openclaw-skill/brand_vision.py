"""Direct brand compliance analysis via Gemini Vision.

Bypasses the orchestrator for maximum efficiency:
- Loads brand DNA from Bluewave API
- Sends image + brand rules directly to Gemini Vision
- Returns structured compliance report
"""

import base64
import json
import logging
import os
from typing import Optional

import httpx
from gemini_cli_engine import gemini_vision

logger = logging.getLogger("openclaw.brand_vision")

async def get_brand_guidelines() -> Optional[dict]:
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
    if guidelines.get("tone_description"):
        parts.append(f"TONE: {guidelines['tone_description'][:200]}")
    return "\n".join(parts)


async def analyze_brand_compliance(image_b64: str, media_type: str = "image/jpeg") -> str:
    """Analyze an image against brand guidelines using Gemini Vision."""
    guidelines = await get_brand_guidelines()
    if not guidelines:
        return "No brand guidelines configured."

    brand_rules = build_brand_prompt(guidelines)
    brand_name = (guidelines.get("custom_rules") or {}).get("brand_name", "the brand")

    prompt = (
        f"You are a senior brand compliance analyst for {brand_name}.\n"
        "Analyze this image for brand compliance across Colors, Typography, Logo, Tone, Composition.\n"
        f"BRAND DNA:\n{json.dumps(guidelines)[:2000]}\n"
        f"RULES:\n{brand_rules}\n"
        "Return a professional report. NO emojis."
    )

    try:
        # Use our helper
        result = await gemini_vision(image_b64, prompt, media_type)
        return f"COMPLIANCE REPORT — {brand_name}\n\n" + result
    except Exception as e:
        logger.error("Brand vision analysis failed: %s", e)
        return f"Analysis failed: {str(e)[:100]}"
