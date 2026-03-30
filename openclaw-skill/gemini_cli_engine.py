"""Gemini CLI Engine — thin wrappers over gemini_engine.gemini_call."""

import asyncio
import logging
import os
from typing import List, Dict, Optional

from gemini_engine import gemini_call

logger = logging.getLogger("openclaw.gemini_cli")


async def cli_call(prompt: str, model: str = "flash", system_prompt: Optional[str] = None) -> str:
    """Single-turn async call. Returns response text."""
    res = await gemini_call(prompt, model=model, system_prompt=system_prompt)
    return res.get("response", "[Error: gemini CLI call failed]")


def cli_call_sync(prompt: str, model: str = "flash", system_prompt: Optional[str] = None) -> str:
    """Synchronous single-turn call for contexts that can't await."""
    return asyncio.run(cli_call(prompt, model=model, system_prompt=system_prompt))


def cli_call_structured(messages: List[Dict], system_prompt: Optional[str] = None, model: str = "flash") -> str:
    """Synchronous structured-history call."""
    if not messages:
        return ""
    last = messages[-1].get("content", "")
    history = messages[:-1] if len(messages) > 1 else None
    return asyncio.run(
        gemini_call(last, model=model, system_prompt=system_prompt, history=history)
    ).get("response", "")


async def gemini_vision(image_b64: bytes, prompt: str, media_type: str = "image/jpeg") -> str:
    """Analyze image via Gemini Vision (uses google-genai SDK directly)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    image_part = types.Part.from_bytes(data=image_b64, mime_type=media_type)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[image_part, prompt],
    )
    return response.text
