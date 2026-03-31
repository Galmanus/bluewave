"""Brand DNA Extractor — extract complete brand identity from raw materials via Gemini.
"""

import base64
import json
import logging
import os
from typing import Optional
from google import genai
from google.genai import types

logger = logging.getLogger("openclaw.brand_dna")

MODEL = "gemini-2.0-pro-exp-02-05"

EXTRACTION_PROMPT = """You are a senior brand strategist. Extract a complete Brand DNA from the materials.
Return EXACT JSON structure with brand_name, positioning, personality, colors, fonts, tone, rules.
Be exhaustive."""

async def extract_brand_dna(
    image_b64: Optional[str] = None,
    media_type: str = "image/jpeg",
    text_content: Optional[str] = None,
    pdf_text: Optional[str] = None,
    brand_name: str = "",
) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key: return {"success": False, "error": "GEMINI_API_KEY not configured"}

    client = genai.Client(api_key=api_key)
    contents = []

    if image_b64:
        contents.append(types.Part.from_bytes(data=image_b64, mime_type=media_type))

    text_parts = []
    if brand_name: text_parts.append(f"Name: {brand_name}")
    if text_content: text_parts.append(f"Description: {text_content}")
    if pdf_text: text_parts.append(f"PDF: {pdf_text}")
    
    contents.append(EXTRACTION_PROMPT)
    contents.append("\n\n".join(text_parts))

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        return {
            "success": True,
            "brand_dna": response.parsed if hasattr(response, "parsed") else json.loads(response.text)
        }
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {"success": False, "error": str(e)}

async def generate_compliance_certificate(brand_name: str, asset_name: str, score: int, dimensions: dict, checked_at: str) -> str:
    # (Remains pure text logic)
    return f"CERTIFICATE: {brand_name} - {score}/100"
