"""On-brand content generation using Gemini.

Generates captions, copies, hashtags, and content variations
that are pre-validated against the brand's voice, tone, and rules.
"""

import json
import logging
import os
from typing import Optional

import httpx
from gemini_engine import gemini_call

logger = logging.getLogger("openclaw.brand_content")

async def get_brand_guidelines() -> Optional[dict]:
    api_url = os.environ.get("BLUEWAVE_API_URL", "http://localhost:8300/api/v1")
    api_key = os.environ.get("BLUEWAVE_API_KEY", "")
    if not api_key: return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{api_url}/brand/guidelines", headers={"X-API-Key": api_key})
            return resp.json() or None
    except: return None

def build_voice_prompt(guidelines: dict) -> str:
    parts = []
    custom = guidelines.get("custom_rules") or {}
    parts.append(f"BRAND: {custom.get('brand_name', 'the brand')}")
    if guidelines.get("tone_description"):
        parts.append(f"TONE: {guidelines['tone_description'][:300]}")
    return "\n".join(parts)

async def generate_content(
    content_type: str,
    context: str = "",
    channel: str = "instagram_feed",
    language: str = "pt-BR",
    variations: int = 1,
) -> str:
    guidelines = await get_brand_guidelines()
    if not guidelines: return "No brand guidelines configured."

    voice = build_voice_prompt(guidelines)
    system_prompt = (
        f"You are the senior copywriter for the brand. Write exactly in this voice:\n{voice}\n"
        f"Channel: {channel}\nLanguage: {language}\n"
        "Output ONLY the content. No meta-commentary."
    )

    user_message = f"Write {content_type} about: {context}. Variations: {variations}"
    
    res = await gemini_call(user_message, system_prompt=system_prompt, model="flash")
    return res.get("response", "Failed to generate content.")
