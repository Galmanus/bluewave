"""Vision — Wave sees images through Claude's eyes."""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict

import anthropic
import httpx

logger = logging.getLogger("openclaw.skills.vision")

MODEL = os.environ.get("OPENCLAW_MODEL", "claude-sonnet-4-20250514")


async def _download_image(url: str) -> tuple:
    """Download image and return (base64_data, media_type)."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    # Normalize media type
    media_map = {
        "image/jpg": "image/jpeg",
        "image/png": "image/png",
        "image/gif": "image/gif",
        "image/webp": "image/webp",
    }
    media_type = media_map.get(content_type, "image/jpeg")
    b64 = base64.standard_b64encode(resp.content).decode("utf-8")
    return b64, media_type


def _call_vision(b64_data: str, media_type: str, prompt: str) -> str:
    """Call Claude with an image and return the response text."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64_data,
                    },
                },
                {
                    "type": "text",
                    "text": prompt,
                },
            ],
        }],
    )
    return response.content[0].text


async def analyze_image(params: Dict[str, Any]) -> Dict:
    """Analyze an image using Claude Vision. Accepts URL or base64."""
    image_url = params.get("image_url", "")
    image_base64 = params.get("image_base64", "")
    media_type = params.get("media_type", "image/jpeg")
    prompt = params.get("prompt", "Describe this image in detail. What do you see?")

    if not image_url and not image_base64:
        return {"success": False, "data": None, "message": "Need image_url or image_base64"}

    try:
        if image_url and not image_base64:
            image_base64, media_type = await _download_image(image_url)

        analysis = _call_vision(image_base64, media_type, prompt)

        return {
            "success": True,
            "data": {"analysis": analysis, "media_type": media_type},
            "message": analysis,
        }
    except Exception as e:
        logger.error("Vision failed: %s", e)
        return {"success": False, "data": None, "message": "Vision analysis failed: %s" % str(e)}


async def analyze_image_for_brand(params: Dict[str, Any]) -> Dict:
    """Analyze an image for brand compliance — colors, logo, typography, tone."""
    image_url = params.get("image_url", "")
    image_base64 = params.get("image_base64", "")
    media_type = params.get("media_type", "image/jpeg")
    brand_guidelines = params.get("brand_guidelines", "")

    if not image_url and not image_base64:
        return {"success": False, "data": None, "message": "Need image_url or image_base64"}

    prompt = (
        "You are a brand compliance expert. Analyze this image and provide:\n\n"
        "1. COLORS: List all dominant colors with hex codes\n"
        "2. TYPOGRAPHY: Any text visible — font style, size hierarchy\n"
        "3. COMPOSITION: Layout, visual hierarchy, balance\n"
        "4. MOOD/TONE: What feeling does this convey?\n"
        "5. OBJECTS/ELEMENTS: Key visual elements\n"
        "6. QUALITY: Resolution, professionalism, production value\n"
    )
    if brand_guidelines:
        prompt += "\n7. COMPLIANCE: Compare against these brand guidelines:\n%s\n" % brand_guidelines
        prompt += "Score compliance 0-100 and list specific issues.\n"

    try:
        if image_url and not image_base64:
            image_base64, media_type = await _download_image(image_url)

        analysis = _call_vision(image_base64, media_type, prompt)
        return {
            "success": True,
            "data": {"analysis": analysis},
            "message": analysis,
        }
    except Exception as e:
        return {"success": False, "data": None, "message": "Brand analysis failed: %s" % str(e)}


async def compare_images(params: Dict[str, Any]) -> Dict:
    """Compare two images — for A/B testing, before/after, competitor analysis."""
    image_url_1 = params.get("image_url_1", "")
    image_url_2 = params.get("image_url_2", "")
    comparison_prompt = params.get("prompt", "Compare these two images. Which is more effective for marketing and why?")

    if not image_url_1 or not image_url_2:
        return {"success": False, "data": None, "message": "Need image_url_1 and image_url_2"}

    try:
        b64_1, mt_1 = await _download_image(image_url_1)
        b64_2, mt_2 = await _download_image(image_url_2)

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mt_1, "data": b64_1}},
                    {"type": "image", "source": {"type": "base64", "media_type": mt_2, "data": b64_2}},
                    {"type": "text", "text": comparison_prompt},
                ],
            }],
        )
        analysis = response.content[0].text
        return {"success": True, "data": {"analysis": analysis}, "message": analysis}
    except Exception as e:
        return {"success": False, "data": None, "message": "Comparison failed: %s" % str(e)}


async def read_text_from_image(params: Dict[str, Any]) -> Dict:
    """OCR — extract all text from an image."""
    image_url = params.get("image_url", "")
    image_base64 = params.get("image_base64", "")
    media_type = params.get("media_type", "image/jpeg")

    if not image_url and not image_base64:
        return {"success": False, "data": None, "message": "Need image_url or image_base64"}

    try:
        if image_url and not image_base64:
            image_base64, media_type = await _download_image(image_url)

        text = _call_vision(
            image_base64, media_type,
            "Extract ALL text visible in this image. Return it exactly as written, preserving layout where possible. If no text is visible, say 'No text found'."
        )
        return {"success": True, "data": {"text": text}, "message": text}
    except Exception as e:
        return {"success": False, "data": None, "message": "OCR failed: %s" % str(e)}


TOOLS = [
    {
        "name": "analyze_image",
        "description": "Analyze any image using Claude Vision. Describe contents, detect objects, read text, assess quality. Accepts image URL or base64. Use for understanding visual content.",
        "handler": analyze_image,
        "parameters": {
            "type": "object",
            "properties": {
                "image_url": {"type": "string", "description": "URL of the image to analyze"},
                "image_base64": {"type": "string", "description": "Base64-encoded image data (alternative to URL)"},
                "media_type": {"type": "string", "default": "image/jpeg", "description": "MIME type (image/jpeg, image/png, image/webp, image/gif)"},
                "prompt": {"type": "string", "default": "Describe this image in detail. What do you see?", "description": "Custom analysis prompt"},
            },
        },
    },
    {
        "name": "analyze_image_for_brand",
        "description": "Analyze an image for brand compliance — colors (with hex), typography, composition, mood, quality. Optionally compare against brand guidelines and score 0-100.",
        "handler": analyze_image_for_brand,
        "parameters": {
            "type": "object",
            "properties": {
                "image_url": {"type": "string", "description": "URL of the image"},
                "image_base64": {"type": "string", "description": "Base64-encoded image (alternative to URL)"},
                "media_type": {"type": "string", "default": "image/jpeg"},
                "brand_guidelines": {"type": "string", "description": "Brand guidelines to check against (colors, fonts, tone, dos/donts)"},
            },
        },
    },
    {
        "name": "compare_images",
        "description": "Compare two images side by side. Use for A/B testing creatives, before/after comparisons, competitor visual analysis.",
        "handler": compare_images,
        "parameters": {
            "type": "object",
            "properties": {
                "image_url_1": {"type": "string", "description": "First image URL"},
                "image_url_2": {"type": "string", "description": "Second image URL"},
                "prompt": {"type": "string", "default": "Compare these two images. Which is more effective for marketing and why?"},
            },
            "required": ["image_url_1", "image_url_2"],
        },
    },
    {
        "name": "read_text_from_image",
        "description": "OCR — extract all text from an image. Use for reading screenshots, documents, signs, labels, social media posts.",
        "handler": read_text_from_image,
        "parameters": {
            "type": "object",
            "properties": {
                "image_url": {"type": "string", "description": "URL of the image"},
                "image_base64": {"type": "string", "description": "Base64-encoded image (alternative to URL)"},
                "media_type": {"type": "string", "default": "image/jpeg"},
            },
        },
    },
]
