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


def compress_image_b64(image_b64: str, max_bytes: int = 4_500_000) -> tuple:
    """Compress image if it exceeds max_bytes. Returns (b64, media_type)."""
    raw = base64.b64decode(image_b64)
    if len(raw) <= max_bytes:
        return image_b64, "image/jpeg"

    from PIL import Image
    import io

    img = Image.open(io.BytesIO(raw))
    # Resize if very large
    max_dim = 2048
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    # Compress as JPEG
    for quality in [85, 70, 50, 30]:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
        if buf.tell() <= max_bytes:
            return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"

    # Last resort: aggressive resize
    img.thumbnail((1024, 1024), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=50)
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"


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

    # Compress image if too large for Claude Vision (5MB limit)
    image_b64, media_type = compress_image_b64(image_b64)

    # Load the full brand DNA JSON for the professional compliance prompt
    brand_dna_json = json.dumps(guidelines, ensure_ascii=False, indent=2)

    system_prompt = (
        f"You are a senior brand compliance analyst for {brand_name}.\n\n"
        "STRICT FORMAT RULES:\n"
        "- NEVER use emojis. Not one. Zero.\n"
        "- NEVER use markdown tables (they render badly). Use structured text instead.\n"
        "- Use ## for section headers, **bold** for emphasis, - for lists.\n"
        "- Write like a professional consultant delivering a report to a CMO. Clean, precise, authoritative.\n"
        "- Use --- to separate sections.\n\n"
        "ANALYSIS PROTOCOL (8 dimensions):\n\n"
        "## 1. COLORS (weight: 20%)\n"
        "Extract dominant colors as hex. Compare each with approved palette using Delta-E.\n"
        "List each color found, its nearest approved match, and the Delta-E distance.\n"
        "Flag any color not in palette. Check WCAG contrast ratios.\n\n"
        "## 2. TYPOGRAPHY (weight: 15%)\n"
        "Identify visible fonts. Compare with approved list. Check hierarchy and weights.\n\n"
        "## 3. LOGO (weight: 15%)\n"
        "Check presence, version, protection area, minimum size.\n\n"
        "## 4. TONE (weight: 15%)\n"
        "Does the mood match the brand personality? Analyze visual tone vs brand voice.\n\n"
        "## 5. COMPOSITION (weight: 10%)\n"
        "Rule of thirds, visual hierarchy, gestalt, spacing, balance.\n\n"
        "## 6. PHOTOGRAPHY (weight: 10%)\n"
        "Style, saturation, lighting, framing vs brand standards.\n\n"
        "## 7. STRATEGIC COHERENCE (weight: 10%)\n"
        "Alignment with brand values, archetypes, personas, positioning.\n\n"
        "## 8. CHANNEL ADEQUACY (weight: 5%)\n"
        "Format and style appropriate for the intended channel.\n\n"
        "SCORING: Each dimension 0-100. Weighted total.\n"
        "VERDICT: APPROVED (>=90, 0 critical) | APPROVED WITH NOTES (>=70) | REJECTED (<70)\n\n"
        "OUTPUT FORMAT:\n"
        "Start with: COMPLIANCE REPORT — [brand name]\n"
        "Then: Overall Score: XX/100 — VERDICT\n"
        "Then each dimension as a section with score, status, findings, and fixes.\n"
        "End with: PRIORITY CORRECTIONS (numbered list, most urgent first)\n"
        "Then: WHAT WORKS (brief list of positives)\n\n"
        "Be PRECISE (hex codes, Delta-E values, contrast ratios). Be CONSTRUCTIVE.\n"
        "Respond in the SAME LANGUAGE as the brand rules."
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
