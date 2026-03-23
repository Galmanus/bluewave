"""
Groq Engine — Ultra-fast LLM inference as backup/complement to Claude.

Groq runs Llama/Mixtral at 500+ tokens/sec — 10x faster than any other provider.
Free tier is generous. Perfect for:
- Swarm simulations (many small calls)
- Bulk analysis
- When Claude CLI is slow or timing out

Setup: GROQ_API_KEY env var from https://console.groq.com/
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("openclaw.groq")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


async def groq_chat(params: Dict[str, Any]) -> Dict:
    """Send a message to Groq for ultra-fast inference."""
    message = params.get("message", "")
    system = params.get("system", "You are a helpful assistant.")
    model = params.get("model", DEFAULT_MODEL)
    max_tokens = min(int(params.get("max_tokens", 2000)), 4000)

    if not message:
        return {"success": False, "data": None, "message": "Need a message"}

    if not GROQ_API_KEY:
        return {"success": False, "data": None, "message": "GROQ_API_KEY not configured. Get one free at console.groq.com"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(GROQ_URL, json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": message},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }, headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            })
            data = r.json()

        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return {
            "success": True,
            "data": {
                "response": response,
                "model": model,
                "tokens": usage.get("total_tokens", 0),
                "speed": f"{usage.get('completion_tokens', 0) / max(data.get('usage', {}).get('completion_time', 1), 0.01):.0f} tok/s" if "completion_time" in usage else "fast",
            },
            "message": f"Groq response ({usage.get('total_tokens', 0)} tokens)"
        }
    except Exception as e:
        logger.error("Groq failed: %s", e)
        return {"success": False, "data": None, "message": str(e)}


async def groq_analyze(params: Dict[str, Any]) -> Dict:
    """Analyze text using Groq — fast bulk analysis."""
    text = params.get("text", "")
    task = params.get("task", "Summarize the key points")

    if not text:
        return {"success": False, "data": None, "message": "Need text to analyze"}

    return await groq_chat({
        "message": f"Task: {task}\n\nText:\n{text[:3000]}",
        "system": "You are an analytical AI. Be concise and specific.",
        "max_tokens": 1000,
    })


TOOLS = [
    {
        "name": "groq_chat",
        "description": "Ultra-fast LLM inference via Groq (500+ tok/s). Use for quick analysis, bulk processing, or when Claude is slow.",
        "parameters": {
            "message": "string — the message/question",
            "system": "string — system prompt (optional)",
            "model": "string — model (default: llama-3.3-70b-versatile)",
            "max_tokens": "int — max response tokens (default 2000)",
        },
        "handler": groq_chat,
    },
    {
        "name": "groq_analyze",
        "description": "Analyze text using Groq — 10x faster than Claude for bulk analysis.",
        "parameters": {
            "text": "string — text to analyze",
            "task": "string — what to analyze (default: summarize)",
        },
        "handler": groq_analyze,
    },
]
