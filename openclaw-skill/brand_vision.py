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
from typing import Optional

import anthropic
import httpx

logger = logging.getLogger("openclaw.brand_vision")

HAIKU = "claude-haiku-4-5-20251001"


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

    # Load the full brand DNA JSON for the professional compliance prompt
    brand_dna_json = json.dumps(guidelines, ensure_ascii=False, indent=2)

    system_prompt = (
        f"You are the Guardian — a Brand Compliance Analyst for {brand_name}.\n\n"
        "Expertise: color science (CIELAB, Delta-E), typography (Vox-ATypI), "
        "visual semiotics, WCAG accessibility, composition (rule of thirds, gestalt).\n\n"
        "PROTOCOL:\n"
        "1. COLORS: Extract dominant colors, compare with approved palette, check contrast\n"
        "2. TYPOGRAPHY: Identify fonts, check hierarchy, verify approved weights\n"
        "3. LOGO: Check presence, version, protection area, minimum size\n"
        "4. TONE: Analyze if mood matches brand personality\n"
        "5. COMPOSITION: Evaluate visual hierarchy, spacing, balance\n"
        "6. PHOTOGRAPHY: Check style, filters, saturation, framing\n"
        "7. STRATEGIC COHERENCE: Alignment with brand values and archetypes\n\n"
        "For each dimension, assign: CONFORME | ALERTA | VIOLACAO\n"
        "Score 0-100 (weighted: colors 20%, typography 15%, logo 15%, tone 15%, "
        "composition 10%, photography 10%, strategy 10%, channel 5%)\n\n"
        "VERDICT: APROVADO (>=90, 0 critical) | APROVADO_COM_RESSALVAS (>=70, max 1 critical) | REPROVADO (<70 or 2+ critical)\n\n"
        "Be PRECISE (hex codes, Delta-E, contrast ratios). Be CONSTRUCTIVE (clear fixes). "
        "PRIORITIZE issues by impact. CELEBRATE what works.\n"
        "Respond in the SAME LANGUAGE as the brand rules (Portuguese if brand is Brazilian)."
    )

    try:
        response = client.messages.create(
            model=HAIKU,
            max_tokens=2000,
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
                            "text": f"Analyze this image for brand compliance.\n\nBRAND DNA:\n{brand_dna_json[:3000]}\n\nBRAND RULES SUMMARY:\n{brand_rules}",
                        },
                    ],
                }
            ],
        )

        return response.content[0].text

    except Exception as e:
        logger.error("Brand vision analysis failed: %s", e)
        return f"Analysis failed: {str(e)[:100]}"
